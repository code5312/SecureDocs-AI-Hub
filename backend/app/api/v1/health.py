from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.dependencies.health import collect_health

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    services: dict[str, str]


@router.get("", response_model=HealthResponse)
def get_health() -> JSONResponse:
    """Return application dependency health with consistent status semantics."""
    services = collect_health()
    is_healthy = all(state == "up" for state in services.values())
    body = {"status": "healthy" if is_healthy else "unhealthy", "services": services}
    return JSONResponse(
        status_code=status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        content=body,
    )
