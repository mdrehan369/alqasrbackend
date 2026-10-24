from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.v1.endpoints.auth import get_current_user_controller
from app.core.api_response import ApiResponse
from app.db.session import get_db
from app.schemas.stats import DashboardBasicStatsResponse
from app.services.stats import get_basic_dashboard_stats_service
from app.utils.constants import HTTP_STATUS_CODES

router = APIRouter(tags=["stats"], dependencies=[Depends(get_current_user_controller)])


@router.get(
    "/dashboard",
    status_code=HTTP_STATUS_CODES.SUCCESS.value,
    response_model=ApiResponse[DashboardBasicStatsResponse],
    summary="It returns the basic dashboard stats to overview the system",
    response_description="It returns it in the dictionary format",
    description="It fetches the basic stats like total products, total catalog value, low stock items and active categories and sends them to the frontend",
)
async def get_basic_dashboard_stats_controller(session: AsyncSession = Depends(get_db)):
    result = await get_basic_dashboard_stats_service(session)
    return ApiResponse[DashboardBasicStatsResponse](
        data=DashboardBasicStatsResponse.model_validate(result)
    )
