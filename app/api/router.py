from fastapi import APIRouter

from app.api.routes.contacts import router as contacts_router
from app.api.routes.conversations import router as conversations_router
from app.api.routes.messages import router as messages_router
from app.api.routes.organizations import router as organizations_router
from app.api.routes.system import router as system_router
from app.api.routes.users import router as users_router

# This file defines the main API router that includes all the individual route modules.

api_router = APIRouter(
    prefix="/api/v1",
)

api_router.include_router(system_router)
api_router.include_router(organizations_router)
api_router.include_router(users_router)
api_router.include_router(contacts_router)
api_router.include_router(conversations_router)
api_router.include_router(messages_router)
