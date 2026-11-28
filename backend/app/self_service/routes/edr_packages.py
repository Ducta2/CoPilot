from fastapi import APIRouter
from fastapi import Depends
from fastapi import Path
from fastapi import Query
from fastapi import Request
from fastapi import Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.self_service.schema.edr_packages import EdrPackageCreate
from app.self_service.schema.edr_packages import EdrPackageListResponse
from app.self_service.schema.edr_packages import EdrPackageResponse
from app.self_service.services import edr_packages as service
from app.time_utils import now_utc

self_service_edr_router = APIRouter()

# Self service for the SOC and the customer alike. The customer is named in the query or the
# body, or is the package's own, so the services check it (404 outside the caller's customers).
SELF_SERVICE = Security(AuthHandler().require_any_scope("admin", "analyst", "customer_user"))


@self_service_edr_router.get(
    "/edr_packages",
    response_model=EdrPackageListResponse,
    description="EDR installer packages of a customer, newest first. Level 1: expiry and install cap are not enforced yet.",
    dependencies=[SELF_SERVICE],
)
async def list_edr_packages(
    customer_code: str = Query(..., min_length=1, max_length=50),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EdrPackageListResponse:
    rows = await service.list_packages(session, current_user, customer_code)
    now = now_utc()
    return EdrPackageListResponse(
        packages=[service.to_schema(row, now) for row in rows],
        success=True,
        message=f"{len(rows)} bộ cài",
    )


@self_service_edr_router.post(
    "/edr_packages",
    response_model=EdrPackageResponse,
    description="Create an EDR installer package. Level 1: a record only, its limits are not enforced yet.",
    dependencies=[SELF_SERVICE],
)
async def create_edr_package(
    body: EdrPackageCreate,
    request: Request,
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EdrPackageResponse:
    row = await service.create_package(session, current_user, body, request)
    return EdrPackageResponse(package=service.to_schema(row), success=True, message="Đã tạo bộ cài")


@self_service_edr_router.delete(
    "/edr_packages/{package_id}",
    response_model=EdrPackageResponse,
    description="Revoke an EDR installer package (soft, idempotent). Level 1: only hides it.",
    dependencies=[SELF_SERVICE],
)
async def revoke_edr_package(
    request: Request,
    package_id: str = Path(..., min_length=1, max_length=20),
    current_user: User = Depends(AuthHandler().get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EdrPackageResponse:
    row = await service.revoke_package(session, current_user, package_id, request)
    return EdrPackageResponse(package=service.to_schema(row), success=True, message="Đã thu hồi bộ cài")
