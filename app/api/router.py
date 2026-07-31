from fastapi import APIRouter

from app.api.routes.organizations import router as organizations_router
from app.api.routes.system import router as system_router

# This file defines the main API router that includes all the individual route modules.

api_router = APIRouter(
    prefix="/api/v1",
)

api_router.include_router(system_router)
api_router.include_router(organizations_router)
