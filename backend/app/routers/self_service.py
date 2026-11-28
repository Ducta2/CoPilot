from fastapi import APIRouter

from app.self_service.routes.edr_packages import self_service_edr_router

# Instantiate the APIRouter
router = APIRouter()

# Self Service: EDR installer packages (Level 1). Sensors are deferred.
router.include_router(self_service_edr_router, prefix="/self_service", tags=["self-service"])
