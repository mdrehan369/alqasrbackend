from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api_response import ApiResponse
from app.core.settings import get_settings
from app.db.session import get_db
from app.schemas.health import HealthData
from app.services.health import check_database_service
from app.utils.constants import (
    HEALTH_STATUS,
    HTTP_RESPONSE_MESSAGES,
    HTTP_STATUS_CODES,
)

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get(
    "/health",
    status_code=HTTP_STATUS_CODES.SUCCESS.value,
    response_model=ApiResponse[HealthData],
    summary="Liveness check",
    description=(
        "Reports that the process is running. Performs no dependency checks, so "
        "it stays fast and is safe to use as a liveness probe."
    ),
    response_description="The service is up.",
)
async def health_liveness_controller():
    return ApiResponse[HealthData](
        message=HTTP_RESPONSE_MESSAGES.SUCCESS.value,
        data=HealthData(
            status=HEALTH_STATUS.HEALTHY.value,
            version=settings.app_version,
        ),
    )


@router.get(
    "/health/ready",
    status_code=HTTP_STATUS_CODES.SUCCESS.value,
    response_model=ApiResponse[HealthData],
    summary="Readiness check",
    description=(
        "Checks the dependencies required to serve traffic. Verifies database "
        "connectivity; returns 503 when a dependency is unavailable."
    ),
    response_description="The service and its dependencies are ready.",
    responses={
        HTTP_STATUS_CODES.SERVICE_UNAVAILABLE.value: {
            "model": ApiResponse[HealthData],
            "description": "One or more dependencies are unavailable.",
        },
    },
)
async def health_readiness_controller(
    response: Response, session: AsyncSession = Depends(get_db)
):
    database = await check_database_service(session)
    is_healthy = database.status == HEALTH_STATUS.UP.value

    data = HealthData(
        status=(
            HEALTH_STATUS.HEALTHY.value
            if is_healthy
            else HEALTH_STATUS.UNHEALTHY.value
        ),
        version=settings.app_version,
        checks={"database": database},
    )

    if not is_healthy:
        response.status_code = HTTP_STATUS_CODES.SERVICE_UNAVAILABLE.value
        return ApiResponse[HealthData](
            success=False,
            message=HTTP_RESPONSE_MESSAGES.SERVICE_UNAVAILABLE.value,
            data=data,
        )

    return ApiResponse[HealthData](
        message=HTTP_RESPONSE_MESSAGES.SUCCESS.value,
        data=data,
    )
