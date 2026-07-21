
from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings



def create_application() -> FastAPI:
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        description="AI-powered support operations backend.",
        version=settings.app_version,
    )

    application.include_router(api_router)


    return application


app = create_application()
