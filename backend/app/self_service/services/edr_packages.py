"""EDR installer packages a customer issues itself (Self Service, Level 1).

Level 1 keeps records only: the install command still uses the customer's shared enrollment
password, so the expiry and the install cap are not enforced on the monitoring server, and
revoking only hides the package. Every package says so with ``enforced=False``. ``enrolled``
stays 0 until the agent sync counts enrollments per package (not built yet).

Tenancy: the customer is named in the query (list) or the body (create), or is the package's
own (revoke), so it is checked here rather than by a path dependency. Anything outside the
caller's customers is a 404, never a 403, so a package id reveals nothing.
"""

import os
import secrets
import time
from base64 import b32encode
from collections import defaultdict
from collections import deque
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Callable
from typing import Deque
from typing import Dict
from typing import Hashable
from typing import List
from typing import Optional

from fastapi import HTTPException
from fastapi import Request
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models.audit import AuditAction
from app.audit.services.audit import record_audit_event
from app.auth.models.users import User
from app.db.universal_models import Customers
from app.db.universal_models import SelfServiceEdrPackage
from app.middleware.customer_access import customer_access_handler
from app.self_service.schema.edr_packages import EdrPackageCreate
from app.self_service.schema.edr_packages import EdrPackageOut
from app.time_utils import now_utc
from app.time_utils import to_naive_utc

QUOTA_ENV = "SELF_SERVICE_EDR_INSTALL_QUOTA"
DEFAULT_QUOTA = 1000
CREATES_PER_WINDOW = 10
WINDOW_SECONDS = 60
_ID_ATTEMPTS = 5

PACKAGE_NOT_FOUND = "Không tìm thấy bộ cài."
CUSTOMER_NOT_FOUND = "Không tìm thấy khách hàng."
TOO_MANY_CREATES = "Bạn tạo bộ cài quá nhanh. Vui lòng thử lại sau ít phút."


class SlidingWindowLimiter:
    """At most ``limit`` hits per key in any ``window_seconds``, in process.

    One backend process serves the API, so an in-memory window is enough to stop a burst; a
    restart forgets it, which is acceptable for an abuse guard.
    """

    def __init__(self, limit: int, window_seconds: float, clock: Callable[[], float] = time.monotonic):
        self.limit = limit
        self.window_seconds = window_seconds
        self._clock = clock
        self._hits: Dict[Hashable, Deque[float]] = defaultdict(deque)

    def hit(self, key: Hashable) -> bool:
        """Count a hit for ``key``; False (and not counted) when the window is already full."""
        now = self._clock()
        hits = self._hits[key]
        while hits and hits[0] <= now - self.window_seconds:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        return True

    def reset(self) -> None:
        self._hits.clear()


create_limiter = SlidingWindowLimiter(CREATES_PER_WINDOW, WINDOW_SECONDS)


def install_quota() -> int:
    """The deployment-wide cap on a customer's open install slots (``SELF_SERVICE_EDR_INSTALL_QUOTA``)."""
    raw = os.getenv(QUOTA_ENV)
    if raw is None or raw.strip() == "":
        return DEFAULT_QUOTA
    try:
        value = int(raw)
    except ValueError:
        logger.warning(f"{QUOTA_ENV}={raw!r} is not an integer; using {DEFAULT_QUOTA}")
        return DEFAULT_QUOTA
    if value < 0:
        logger.warning(f"{QUOTA_ENV}={value} is negative; using {DEFAULT_QUOTA}")
        return DEFAULT_QUOTA
    return value


def new_package_id() -> str:
    """``PKG-`` and 8 random base32 characters (40 bits)."""
    return "PKG-" + b32encode(secrets.token_bytes(5)).decode("ascii")


def package_status(row, now: datetime) -> str:
    """``revoked`` if revoked, ``expired`` once ``expires_at`` is reached, else ``active``."""
    if row.revoked_at is not None:
        return "revoked"
    if to_naive_utc(now) >= to_naive_utc(row.expires_at):
        return "expired"
    return "active"


def _utc(moment: datetime) -> datetime:
    """A stored naive UTC time as an aware one, so the Console never reads it as local time."""
    return moment.replace(tzinfo=timezone.utc) if moment.tzinfo is None else moment.astimezone(timezone.utc)


def to_schema(row: SelfServiceEdrPackage, now: Optional[datetime] = None) -> EdrPackageOut:
    return EdrPackageOut(
        id=row.id,
        customer_code=row.customer_code,
        platform=row.platform,
        arch=row.arch,
        group=row.group,
        created_by=row.created_by,
        created_at=_utc(row.created_at),
        expires_at=_utc(row.expires_at),
        max_installs=row.max_installs,
        enrolled=row.enrolled,
        status=package_status(row, now or now_utc()),
        enforced=False,
    )


async def _require_customer(session: AsyncSession, user: User, customer_code: str) -> None:
    """404 unless the caller may see ``customer_code`` and it exists."""
    if not await customer_access_handler.check_customer_access(user, customer_code, session):
        raise HTTPException(status_code=404, detail=CUSTOMER_NOT_FOUND)
    found = await session.execute(select(Customers.customer_code).where(Customers.customer_code == customer_code))
    if found.scalars().first() is None:
        raise HTTPException(status_code=404, detail=CUSTOMER_NOT_FOUND)


async def list_packages(session: AsyncSession, user: User, customer_code: str) -> List[SelfServiceEdrPackage]:
    await _require_customer(session, user, customer_code)
    result = await session.execute(
        select(SelfServiceEdrPackage)
        .where(SelfServiceEdrPackage.customer_code == customer_code)
        .order_by(SelfServiceEdrPackage.created_at.desc(), SelfServiceEdrPackage.id),
    )
    return list(result.scalars().all())


async def _open_slots(session: AsyncSession, customer_code: str, now: datetime) -> int:
    """Install slots still open on the customer's active packages: ``max_installs - enrolled`` each."""
    result = await session.execute(
        select(SelfServiceEdrPackage.max_installs, SelfServiceEdrPackage.enrolled).where(
            SelfServiceEdrPackage.customer_code == customer_code,
            SelfServiceEdrPackage.revoked_at.is_(None),
            SelfServiceEdrPackage.expires_at > now,
        ),
    )
    return sum(max(issued - (enrolled or 0), 0) for issued, enrolled in result.all())


async def _unused_id(session: AsyncSession) -> str:
    for _ in range(_ID_ATTEMPTS):
        candidate = new_package_id()
        if await session.get(SelfServiceEdrPackage, candidate) is None:
            return candidate
        logger.warning(f"EDR package id collision on {candidate}; drawing again")
    raise HTTPException(status_code=503, detail="Không tạo được mã bộ cài. Vui lòng thử lại.")


async def create_package(
    session: AsyncSession, user: User, body: EdrPackageCreate, request: Optional[Request] = None
) -> SelfServiceEdrPackage:
    if not create_limiter.hit(user.id):
        raise HTTPException(status_code=429, detail=TOO_MANY_CREATES)
    await _require_customer(session, user, body.customer_code)

    now = to_naive_utc(now_utc()).replace(microsecond=0)
    quota = install_quota()
    used = await _open_slots(session, body.customer_code, now)
    if used + body.max_installs > quota:
        remaining = max(quota - used, 0)
        raise HTTPException(
            status_code=409,
            detail=f"Vượt hạn mức lượt cài của khách hàng: còn {remaining} lượt, yêu cầu {body.max_installs} lượt.",
        )

    row = SelfServiceEdrPackage(
        id=await _unused_id(session),
        customer_code=body.customer_code,
        platform=body.platform.value,
        arch=body.arch,
        group=body.group or body.customer_code,
        max_installs=body.max_installs,
        enrolled=0,
        created_by=user.username,
        created_at=now,
        expires_at=now + timedelta(days=body.valid_days),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    logger.info(f"EDR package created: id={row.id} customer={row.customer_code} max_installs={row.max_installs} by user={user.id}")
    await record_audit_event(
        action=AuditAction.SELF_SERVICE_EDR_PACKAGE_CREATE,
        actor_user_id=user.id,
        actor_username=user.username,
        customer_code=row.customer_code,
        entity_type="edr_package",
        entity_id=row.id,
        new_value={
            "platform": row.platform,
            "arch": row.arch,
            "group": row.group,
            "max_installs": row.max_installs,
            "valid_days": body.valid_days,
            "expires_at": row.expires_at.isoformat(),
        },
        request=request,
    )
    return row


async def revoke_package(session: AsyncSession, user: User, package_id: str, request: Optional[Request] = None) -> SelfServiceEdrPackage:
    """Soft revoke: stamps ``revoked_at`` once; revoking again changes nothing and is not audited."""
    row = await session.get(SelfServiceEdrPackage, package_id)
    if row is None or not await customer_access_handler.check_customer_access(user, row.customer_code, session):
        raise HTTPException(status_code=404, detail=PACKAGE_NOT_FOUND)
    if row.revoked_at is not None:
        return row

    row.revoked_at = to_naive_utc(now_utc()).replace(microsecond=0)
    row.revoked_by = user.username
    session.add(row)
    await session.commit()
    await session.refresh(row)
    logger.info(f"EDR package revoked: id={row.id} customer={row.customer_code} by user={user.id}")
    await record_audit_event(
        action=AuditAction.SELF_SERVICE_EDR_PACKAGE_REVOKE,
        actor_user_id=user.id,
        actor_username=user.username,
        customer_code=row.customer_code,
        entity_type="edr_package",
        entity_id=row.id,
        old_value={"status": "active" if row.expires_at > row.revoked_at else "expired"},
        new_value={"status": "revoked", "revoked_at": row.revoked_at.isoformat()},
        request=request,
    )
    return row
