import math

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.v1.endpoints.auth import get_current_user_controller
from app.core.api_response import ApiResponse, ErrorResponse
from app.db.session import get_db
from app.schemas.category import (
    CategoryResponse,
    CreateCategoryRequest,
    UpdateCategoryRequest,
)
from app.schemas.pagination import PaginatedResponse, Pagination
from app.services.category import (
    create_category_service,
    delete_category_service,
    get_categories_service,
    update_category_service,
)
from app.utils.constants import HTTP_RESPONSE_MESSAGES, HTTP_STATUS_CODES

router = APIRouter(
    tags=["Category"], dependencies=[Depends(get_current_user_controller)]
)


@router.post(
    "/",
    status_code=HTTP_STATUS_CODES.CREATED.value,
    response_model=ApiResponse[CategoryResponse],
    summary="Create a category",
    description="Creates a new category. Names are compared case-insensitively.",
    response_description="The category that was created.",
    responses={
        HTTP_STATUS_CODES.CONFLICT.value: {
            "model": ErrorResponse,
            "description": "A category with the same name already exists.",
        },
    },
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
    summary="List categories",
    description=(
        "Returns a paginated list of categories, optionally filtered by a "
        "case-insensitive name prefix."
    ),
    response_description="A page of categories with pagination metadata.",
)
async def get_categories_controller(
    session: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-based)."),
    limit: int = Query(
        default=10, ge=1, le=100, description="Number of items per page (max 100)."
    ),
    search: str = Query(
        default="", max_length=100, description="Case-insensitive name prefix filter."
    ),
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


@router.patch(
    "/{category_id}",
    status_code=HTTP_STATUS_CODES.SUCCESS.value,
    response_model=ApiResponse[CategoryResponse],
    summary="Update a category",
    description=(
        "Partially updates a category. Send only the fields to change; omitted "
        "or null fields are left unchanged."
    ),
    response_description="The updated category.",
    responses={
        HTTP_STATUS_CODES.RESOURCE_NOT_FOUND.value: {
            "model": ErrorResponse,
            "description": "Category not found.",
        },
        HTTP_STATUS_CODES.CONFLICT.value: {
            "model": ErrorResponse,
            "description": "Another category already uses that name.",
        },
    },
)
async def update_category_controller(
    payload: UpdateCategoryRequest,
    category_id: int = Path(ge=1, description="Id of the category to update."),
    session: AsyncSession = Depends(get_db),
):
    result = await update_category_service(session, category_id, payload)
    return ApiResponse[CategoryResponse](
        message=HTTP_RESPONSE_MESSAGES.UPDATED.value,
        data=CategoryResponse.model_validate(result),
    )


@router.delete(
    "/{category_id}",
    status_code=HTTP_STATUS_CODES.NO_CONTENT.value,
    summary="Delete a category",
    description=(
        "Deletes a category. Fails if the category still has products assigned."
    ),
    responses={
        HTTP_STATUS_CODES.RESOURCE_NOT_FOUND.value: {
            "model": ErrorResponse,
            "description": "Category not found.",
        },
        HTTP_STATUS_CODES.BAD_REQUEST.value: {
            "model": ErrorResponse,
            "description": "Category still has products and cannot be deleted.",
        },
    },
)
async def delete_category_controller(
    category_id: int = Path(ge=1, description="Id of the category to delete."),
    session: AsyncSession = Depends(get_db),
):
    await delete_category_service(session, category_id)
