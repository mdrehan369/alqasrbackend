import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api_response import ApiResponse
from app.db.session import get_db
from app.schemas.category import CategoryResponse, CreateCategoryRequest
from app.schemas.pagination import PaginatedResponse, Pagination
from app.services.category import create_category_service, get_categories_service
from app.utils.constants import HTTP_RESPONSE_MESSAGES, HTTP_STATUS_CODES

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
        message=HTTP_RESPONSE_MESSAGES.CREATED.value,
        data=CategoryResponse.model_validate(result),
    )


@router.get(
    "/",
    status_code=HTTP_STATUS_CODES.SUCCESS.value,
    response_model=ApiResponse[PaginatedResponse[CategoryResponse]],
)
async def get_categories_controller(
    session: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    search: str = Query(default="", max_length=100),
):
    result, total = await get_categories_service(session, page, limit, search)
    total_pages = math.ceil(total / limit) if total else 0

    return ApiResponse[PaginatedResponse[CategoryResponse]](
        data=PaginatedResponse(
            items=[CategoryResponse.model_validate(c) for c in result],
            pagination=Pagination(
                page=page,
                limit=limit,
                total=total,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1,
            ),
        )
    )
