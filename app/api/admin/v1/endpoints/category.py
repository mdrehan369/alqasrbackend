from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api_response import ApiResponse
from app.db.session import get_db
from app.schemas.category import CategoryResponse, CreateCategoryRequest
from app.services.category import create_category_service, get_categories_service
from app.utils.constants import HTTP_STATUS_CODES

router = APIRouter()


@router.post(
    "/",
    status_code=HTTP_STATUS_CODES.CREATED.value,
    response_model=ApiResponse[CategoryResponse],
)
async def create_category_controller(
    payload: CreateCategoryRequest, session: AsyncSession = Depends(get_db)
):
    result = await create_category_service(session, payload)
    return ApiResponse[CategoryResponse](
        data=CategoryResponse.model_validate(result),
    )


@router.get(
    "/",
    status_code=HTTP_STATUS_CODES.SUCCESS.value,
    response_model=ApiResponse[list[CategoryResponse]],
)
async def get_categories_controller(session: AsyncSession = Depends(get_db)):
    result = await get_categories_service(session)
    return ApiResponse[list[CategoryResponse]](
        data=[CategoryResponse.model_validate(c) for c in result]
    )
