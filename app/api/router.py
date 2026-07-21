from fastapi import APIRouter

from app.api.routes.system import router as system_router

# This file defines the main API router that includes all the individual route modules.

api_router = APIRouter()

api_router.include_router(system_router)