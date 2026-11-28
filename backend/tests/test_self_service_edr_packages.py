"""Self Service: EDR installer packages ("bộ cài EDR"), Level 1 (records only, not enforced).

Real routers, real in-memory database, real request parsing; only token decoding, user lookup
and the audit writer are replaced.

Pinned here:
- ``status`` is computed when read (revoked, then expired, else active) and ``enforced`` is false;
- create: the package's fields, its id, the group defaulting to the customer code, its expiry,
  and an audit row; the input is validated (platform, arch, group, max_installs, valid_days);
- the deployment-wide install quota (``SELF_SERVICE_EDR_INSTALL_QUOTA``) is a 409, and only
  active packages count against it;
- a customer user of A can neither list, create for, nor revoke B's packages: 404, never 403;
- revoking is soft and idempotent, audited once;
- scopes other than admin, analyst and customer_user are refused;
- at most 10 creations a minute per user (429).

Run with: cd backend && python -m pytest tests/test_self_service_edr_packages.py
"""

import asyncio
import os
import re
from datetime import datetime
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402
from sqlmodel import select  # noqa: E402

from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import get_db  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.db.universal_models import SelfServiceEdrPackage  # noqa: E402
from app.self_service.services import edr_packages as service  # noqa: E402

PEOPLE = [(1, "admin", 1), (2, "ana", 2), (5, "cron", 3), (10, "jane", 4), (11, "bob", 4), (12, "globex_jane", 4)]
USERS = {name: SimpleNamespace(id=uid, username=name, role_id=role) for uid, name, role in PEOPLE}
SCOPES = {"admin": ["admin"], "ana": ["analyst"], "cron": ["scheduler"], "jane": ["customer_user"], "bob": ["customer_user"]}
SCOPES["globex_jane"] = ["customer_user"]
TABLES = ["user", "customers", "user_customer_access", "self_service_edr_packages"]
BASE = "/self_service/edr_packages"
BODY = {"customer_code": "ACME", "platform": "windows", "arch": "x64", "group": "servers", "max_installs": 10, "valid_days": 7}


class Db:
    def __init__(self):
        self.engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    async def create(self) -> "Db":
        tables = [SQLModel.metadata.tables[name] for name in TABLES]
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=tables))
        return self

    def session(self) -> AsyncSession:
        return self.factory()


def _app(db: Db) -> FastAPI:
    from app.routers import self_service

    app = FastAPI()
    app.include_router(self_service.router)

    async def _session():
        async with db.session() as session:
            yield session

    app.dependency_overrides[get_db] = _session
    return app


async def _seed(db: Db) -> None:
    async with db.session() as s:
        s.add_all(User(id=uid, username=name, password="x" * 8, email=f"{name}@example.com", role_id=role) for uid, name, role in PEOPLE)
        s.add_all([Customers(customer_code="ACME", customer_name="Acme"), Customers(customer_code="GLOBEX", customer_name="Globex")])
        await s.commit()
        s.add_all(
            [
                UserCustomerAccess(user_id=10, customer_code="ACME"),
                UserCustomerAccess(user_id=11, customer_code="ACME"),
                UserCustomerAccess(user_id=12, customer_code="GLOBEX"),
            ],
        )
        await s.commit()


@pytest.fixture(autouse=True)
def _fresh_limiter():
    service.create_limiter.reset()
    yield
    service.create_limiter.reset()


def call(scenario):
    async def _inner():
        db = await Db().create()
        await _seed(db)
        rec = SimpleNamespace(audit=AsyncMock(), db=db)

        async def resolve_user(self, request, username):
            return USERS.get(username)

        with patch.object(AuthHandler, "decode_token", lambda self, token: (token, SCOPES.get(token, []))), patch.object(
            AuthHandler,
            "_resolve_user",
            resolve_user,
        ), patch("app.self_service.services.edr_packages.record_audit_event", rec.audit):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=_app(db)), base_url="http://test") as client:
                return await scenario(client, rec)

    return asyncio.run(_inner())


def as_user(name):
    return {"Authorization": f"Bearer {name}"}


def create(client, user="jane", **overrides):
    return client.post(BASE, json={**BODY, **overrides}, headers=as_user(user))


async def rows(db: Db):
    async with db.session() as s:
        return (await s.execute(select(SelfServiceEdrPackage))).scalars().all()


async def add_package(db: Db, **fields) -> SelfServiceEdrPackage:
    now = datetime.utcnow().replace(microsecond=0)
    values = dict(
        id="PKG-TESTTEST",
        customer_code="ACME",
        platform="linux",
        arch="x64",
        group="ACME",
        max_installs=10,
        enrolled=0,
        created_by="ana",
        created_at=now,
        expires_at=now + timedelta(days=7),
    )
    values.update(fields)
    async with db.session() as s:
        row = SelfServiceEdrPackage(**values)
        s.add(row)
        await s.commit()
        return row


# ── status, computed when read ────────────────────────────────────────────────


def test_status_is_revoked_then_expired_then_active():
    now = datetime(2026, 11, 28, 12, 0, 0)
    alive = SimpleNamespace(revoked_at=None, expires_at=now + timedelta(seconds=1))
    lapsed = SimpleNamespace(revoked_at=None, expires_at=now)
    revoked = SimpleNamespace(revoked_at=now - timedelta(days=1), expires_at=now - timedelta(days=2))
    assert service.package_status(alive, now) == "active"
    assert service.package_status(lapsed, now) == "expired"
    assert service.package_status(revoked, now) == "revoked"


def test_status_accepts_an_aware_now():
    from datetime import timezone

    now = datetime(2026, 11, 28, 12, 0, 0, tzinfo=timezone.utc)
    row = SimpleNamespace(revoked_at=None, expires_at=datetime(2026, 11, 28, 13, 0, 0))
    assert service.package_status(row, now) == "active"


def test_listing_computes_the_status_of_each_package():
    async def scenario(client, rec):
        now = datetime.utcnow().replace(microsecond=0)
        await add_package(rec.db, id="PKG-AAAAAAAA", created_at=now - timedelta(days=3))
        await add_package(rec.db, id="PKG-BBBBBBBB", created_at=now - timedelta(days=9), expires_at=now - timedelta(days=2))
        await add_package(rec.db, id="PKG-CCCCCCCC", created_at=now - timedelta(days=1), revoked_at=now, revoked_by="ana")
        await add_package(rec.db, id="PKG-DDDDDDDD", customer_code="GLOBEX")
        return await client.get(BASE, params={"customer_code": "ACME"}, headers=as_user("jane"))

    response = call(scenario)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    statuses = {p["id"]: p["status"] for p in body["packages"]}
    assert statuses == {"PKG-AAAAAAAA": "active", "PKG-BBBBBBBB": "expired", "PKG-CCCCCCCC": "revoked"}
    # Newest first.
    assert [p["id"] for p in body["packages"]] == ["PKG-CCCCCCCC", "PKG-AAAAAAAA", "PKG-BBBBBBBB"]
    assert all(p["enforced"] is False for p in body["packages"])


# ── create ────────────────────────────────────────────────────────────────────


def test_a_customer_user_creates_a_package_for_their_customer():
    async def scenario(client, rec):
        response = await create(client)
        return rec, response, await rows(rec.db)

    rec, response, stored = call(scenario)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True and body["message"]
    package = body["package"]
    assert re.fullmatch(r"PKG-[A-Z2-7]{8}", package["id"])
    assert set(package) == {
        "id",
        "customer_code",
        "platform",
        "arch",
        "group",
        "created_by",
        "created_at",
        "expires_at",
        "max_installs",
        "enrolled",
        "status",
        "enforced",
    }
    assert (package["customer_code"], package["platform"], package["arch"], package["group"]) == ("ACME", "windows", "x64", "servers")
    assert (package["max_installs"], package["enrolled"], package["status"], package["enforced"]) == (10, 0, "active", False)
    assert package["created_by"] == "jane"
    created = datetime.fromisoformat(package["created_at"])
    expires = datetime.fromisoformat(package["expires_at"])
    assert created.tzinfo is not None, "timestamps are sent as UTC with an offset"
    assert expires - created == timedelta(days=7)
    assert len(stored) == 1 and stored[0].id == package["id"] and stored[0].revoked_at is None
    audit = rec.audit.await_args.kwargs
    assert audit["action"].value == "self_service.edr_package_create"
    assert (audit["actor_user_id"], audit["actor_username"], audit["customer_code"]) == (10, "jane", "ACME")
    assert (audit["entity_type"], audit["entity_id"]) == ("edr_package", package["id"])
    assert audit["new_value"]["max_installs"] == 10


def test_the_group_defaults_to_the_customer_code():
    async def scenario(client, rec):
        missing = await client.post(BASE, json={k: v for k, v in BODY.items() if k != "group"}, headers=as_user("jane"))
        empty = await create(client, group="")
        return missing, empty

    missing, empty = call(scenario)
    assert missing.status_code == 200, missing.text
    assert missing.json()["package"]["group"] == "ACME"
    assert empty.status_code == 200, empty.text
    assert empty.json()["package"]["group"] == "ACME"


def test_an_admin_and_an_analyst_create_too():
    async def scenario(client, rec):
        return await create(client, user="admin"), await create(client, user="ana", customer_code="GLOBEX")

    by_admin, by_analyst = call(scenario)
    assert by_admin.status_code == 200 and by_admin.json()["package"]["created_by"] == "admin"
    assert by_analyst.status_code == 200 and by_analyst.json()["package"]["customer_code"] == "GLOBEX"


@pytest.mark.parametrize(
    "overrides",
    [
        {"platform": "solaris"},
        {"arch": "riscv"},
        {"group": "bad group"},
        {"group": "x" * 41},
        {"group": "nhóm"},
        {"max_installs": 0},
        {"max_installs": 501},
        {"valid_days": 3},
        {"valid_days": 0},
        {"customer_code": ""},
    ],
)
def test_the_input_is_validated(overrides):
    async def scenario(client, rec):
        return await create(client, **overrides), await rows(rec.db)

    response, stored = call(scenario)
    assert response.status_code == 422, response.text
    assert stored == []


@pytest.mark.parametrize("valid_days", [1, 7, 30])
@pytest.mark.parametrize("platform,arch", [("windows", "x86"), ("linux", "arm64"), ("macos", "arm64")])
def test_accepted_values(platform, arch, valid_days):
    async def scenario(client, rec):
        return await create(client, platform=platform, arch=arch, valid_days=valid_days, max_installs=500)

    response = call(scenario)
    assert response.status_code == 200, response.text


# ── quota ─────────────────────────────────────────────────────────────────────


def test_the_quota_is_a_409_and_only_active_packages_count(monkeypatch):
    monkeypatch.setenv("SELF_SERVICE_EDR_INSTALL_QUOTA", "30")

    async def scenario(client, rec):
        now = datetime.utcnow().replace(microsecond=0)
        # 25 slots used: 20 issued minus 5 enrolled, plus 10; the expired and revoked ones are free.
        await add_package(rec.db, id="PKG-AAAAAAAA", max_installs=20, enrolled=5)
        await add_package(rec.db, id="PKG-BBBBBBBB", max_installs=10)
        await add_package(rec.db, id="PKG-CCCCCCCC", max_installs=400, expires_at=now - timedelta(minutes=1))
        await add_package(rec.db, id="PKG-DDDDDDDD", max_installs=400, revoked_at=now, revoked_by="ana")
        # Another customer's packages do not count.
        await add_package(rec.db, id="PKG-EEEEEEEE", customer_code="GLOBEX", max_installs=400)
        over = await create(client, max_installs=6)
        fits = await create(client, max_installs=5)
        full = await create(client, max_installs=1)
        return over, fits, full, await rows(rec.db)

    over, fits, full, stored = call(scenario)
    assert over.status_code == 409, over.text
    assert fits.status_code == 200, fits.text
    assert full.status_code == 409
    assert len(stored) == 6


def test_the_quota_defaults_to_1000(monkeypatch):
    monkeypatch.delenv("SELF_SERVICE_EDR_INSTALL_QUOTA", raising=False)
    assert service.install_quota() == 1000

    async def scenario(client, rec):
        await add_package(rec.db, id="PKG-AAAAAAAA", max_installs=999)
        return await create(client, max_installs=2), await create(client, max_installs=1)

    over, fits = call(scenario)
    assert over.status_code == 409 and fits.status_code == 200


def test_a_malformed_quota_falls_back_to_the_default(monkeypatch):
    monkeypatch.setenv("SELF_SERVICE_EDR_INSTALL_QUOTA", "lots")
    assert service.install_quota() == 1000
    monkeypatch.setenv("SELF_SERVICE_EDR_INSTALL_QUOTA", "250")
    assert service.install_quota() == 250


# ── tenancy ───────────────────────────────────────────────────────────────────


def test_a_customer_user_cannot_see_create_for_or_revoke_another_customers_packages():
    async def scenario(client, rec):
        await add_package(rec.db, id="PKG-GGGGGGGG", customer_code="GLOBEX")
        listed = await client.get(BASE, params={"customer_code": "GLOBEX"}, headers=as_user("jane"))
        created = await create(client, customer_code="GLOBEX")
        revoked = await client.delete(f"{BASE}/PKG-GGGGGGGG", headers=as_user("jane"))
        missing = await client.delete(f"{BASE}/PKG-NOPENOPE", headers=as_user("jane"))
        unknown_customer = await create(client, user="admin", customer_code="NOPE")
        return rec, listed, created, revoked, missing, unknown_customer, await rows(rec.db)

    rec, listed, created, revoked, missing, unknown_customer, stored = call(scenario)
    assert listed.status_code == 404
    assert created.status_code == 404
    assert revoked.status_code == 404
    assert missing.status_code == 404
    # The two answers are the same, so a package id from another tenant reveals nothing.
    assert revoked.json() == missing.json()
    assert unknown_customer.status_code == 404
    assert len(stored) == 1 and stored[0].revoked_at is None
    rec.audit.assert_not_awaited()


def test_listing_requires_a_customer_code():
    async def scenario(client, rec):
        return await client.get(BASE, headers=as_user("admin"))

    assert call(scenario).status_code == 422


def test_a_customer_user_without_assignments_sees_nothing():
    async def scenario(client, rec):
        USERS["lonely"] = SimpleNamespace(id=13, username="lonely", role_id=4)
        SCOPES["lonely"] = ["customer_user"]
        try:
            return await client.get(BASE, params={"customer_code": "ACME"}, headers=as_user("lonely"))
        finally:
            USERS.pop("lonely")
            SCOPES.pop("lonely")

    assert call(scenario).status_code == 404


# ── revoke ────────────────────────────────────────────────────────────────────


def test_revoking_is_soft_idempotent_and_audited_once():
    async def scenario(client, rec):
        package = (await create(client)).json()["package"]
        rec.audit.reset_mock()
        first = await client.delete(f"{BASE}/{package['id']}", headers=as_user("bob"))
        stored_first = (await rows(rec.db))[0]
        second = await client.delete(f"{BASE}/{package['id']}", headers=as_user("jane"))
        stored_second = (await rows(rec.db))[0]
        listed = await client.get(BASE, params={"customer_code": "ACME"}, headers=as_user("jane"))
        return rec, first, stored_first, second, stored_second, listed

    rec, first, stored_first, second, stored_second, listed = call(scenario)
    assert first.status_code == 200 and first.json()["success"] is True
    assert first.json()["package"]["status"] == "revoked"
    assert second.status_code == 200 and second.json()["success"] is True
    assert stored_first.revoked_at is not None and stored_first.revoked_by == "bob"
    assert (stored_second.revoked_at, stored_second.revoked_by) == (stored_first.revoked_at, "bob")
    assert [p["status"] for p in listed.json()["packages"]] == ["revoked"]
    assert rec.audit.await_count == 1
    audit = rec.audit.await_args.kwargs
    assert audit["action"].value == "self_service.edr_package_revoke"
    assert (audit["actor_username"], audit["customer_code"], audit["entity_id"]) == ("bob", "ACME", stored_first.id)


# ── scopes ────────────────────────────────────────────────────────────────────


def test_other_scopes_are_refused():
    async def scenario(client, rec):
        await add_package(rec.db, id="PKG-AAAAAAAA")
        return [
            await client.get(BASE, params={"customer_code": "ACME"}, headers=as_user("cron")),
            await create(client, user="cron"),
            await client.delete(f"{BASE}/PKG-AAAAAAAA", headers=as_user("cron")),
        ], await client.get(BASE, params={"customer_code": "ACME"})

    refused, anonymous = call(scenario)
    assert [r.status_code for r in refused] == [403, 403, 403]
    assert anonymous.status_code == 401


# ── rate limit ────────────────────────────────────────────────────────────────


def test_at_most_ten_creations_a_minute_per_user(monkeypatch):
    monkeypatch.setenv("SELF_SERVICE_EDR_INSTALL_QUOTA", "100000")

    async def scenario(client, rec):
        allowed = [await create(client, max_installs=1) for _ in range(10)]
        refused = await create(client, max_installs=1)
        other_user = await create(client, user="bob", max_installs=1)
        return allowed, refused, other_user, await rows(rec.db)

    allowed, refused, other_user, stored = call(scenario)
    assert [r.status_code for r in allowed] == [200] * 10
    assert refused.status_code == 429
    assert other_user.status_code == 200
    assert len(stored) == 11


def test_the_limiter_window_slides():
    clock = SimpleNamespace(now=1000.0)
    limiter = service.SlidingWindowLimiter(limit=2, window_seconds=60, clock=lambda: clock.now)
    assert limiter.hit(1) and limiter.hit(1)
    assert not limiter.hit(1)
    assert limiter.hit(2)
    clock.now += 59
    assert not limiter.hit(1)
    clock.now += 2
    assert limiter.hit(1)


# ── ids ───────────────────────────────────────────────────────────────────────


def test_a_colliding_id_is_drawn_again():
    async def scenario(client, rec):
        await add_package(rec.db, id="PKG-AAAAAAAA")
        ids = iter(["PKG-AAAAAAAA", "PKG-BBBBBBBB"])
        with patch.object(service, "new_package_id", lambda: next(ids)):
            return await create(client)

    response = call(scenario)
    assert response.status_code == 200, response.text
    assert response.json()["package"]["id"] == "PKG-BBBBBBBB"


def test_package_ids_look_right():
    ids = {service.new_package_id() for _ in range(200)}
    assert len(ids) == 200
    assert all(re.fullmatch(r"PKG-[A-Z2-7]{8}", i) for i in ids)
