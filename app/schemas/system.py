from typing import Literal

from pydantic import BaseModel

# system health
class HealthResponse(BaseModel):
    status: Literal["ok"]

# system readiness
class ReadinessResponse(BaseModel):
    status: Literal["ready"]