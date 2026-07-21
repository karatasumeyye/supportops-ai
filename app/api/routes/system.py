from fastapi import APIRouter, status

from app.schemas.system import HealthResponse

# This file defines the system API routes. 

router = APIRouter(
    tags=["System"],
)

@router.get(
    "/healthz",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check endpoint",
)

async def health_check() -> HealthResponse:
    return HealthResponse(status="ok")
