from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api_response import ApiResponse
from app.db.session import get_db
from app.schemas.category import (
    CategoryResponseWithProductCnt,
)
from app.services.category import (
    get_all_categories_with_product_count_service,
)
from app.utils.constants import HTTP_STATUS_CODES

router = APIRouter(tags=["Category"])


@router.get(
    "/",
    status_code=HTTP_STATUS_CODES.SUCCESS.value,
    response_model=ApiResponse[list[CategoryResponseWithProductCnt]],
    summary="List categories",
    description=("Returns a list of categories with product counts also."),
    response_description="A page of categories.",
)
async def get_categories_controller(
    session: AsyncSession = Depends(get_db),
):
    result = await get_all_categories_with_product_count_service(session)

    return ApiResponse[list[CategoryResponseWithProductCnt]](
        data=[CategoryResponseWithProductCnt.model_validate(c) for c in result]
    )
