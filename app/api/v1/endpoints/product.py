import math

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api_response import ApiResponse, ErrorResponse
from app.db.session import get_db
from app.schemas.pagination import PaginatedResponse, Pagination
from app.schemas.product import (
    ProductListItemResponse,
    ProductResponse,
    ProductsListFilters,
    SearchableProductFields,
    SortOrder,
)
from app.services.product import (
    get_active_product_by_slug_service,
    get_active_product_service,
    get_products_service,
)
from app.utils.constants import HTTP_RESPONSE_MESSAGES, HTTP_STATUS_CODES

router = APIRouter(tags=["Product"])


@router.get(
    "/",
    status_code=HTTP_STATUS_CODES.SUCCESS.value,
    response_model=ApiResponse[PaginatedResponse[ProductListItemResponse]],
    summary="List products",
    description=(
        "Returns a paginated list of products, optionally filtered by a "
        "case-insensitive name prefix."
    ),
    response_description="A page of products with pagination metadata.",
)
async def get_products_controller(
    session: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-based)."),
    limit: int = Query(
        default=10, ge=1, le=100, description="Number of items per page (max 100)."
    ),
    search: str = Query(
        default=None, max_length=100, description="Case-insensitive prefix filter."
    ),
    search_in: list[SearchableProductFields] = Query(
        default=[SearchableProductFields.TITLE],
        description="Search in array to look for specified fields",
    ),
    category_ids: list[int] = Query(
        default=[], description="The categories to search for"
    ),
    sort_order: SortOrder = Query(
        default=SortOrder.ASC,
        description="The sort order for the field created_at",
    ),
):
    product_filters = ProductsListFilters(
        sort_order=sort_order,
        search=search,
        search_in=search_in,
        category_ids=category_ids,
        is_active=True,
    )
    result, total = await get_products_service(session, page, limit, product_filters)
    total_pages = math.ceil(total / limit) if total else 0

    return ApiResponse[PaginatedResponse[ProductListItemResponse]](
        data=PaginatedResponse(
            items=[ProductListItemResponse.model_validate(c) for c in result],
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


@router.get(
    "/{product_id}",
    status_code=HTTP_STATUS_CODES.SUCCESS.value,
    response_model=ApiResponse[ProductResponse],
    summary="Get a product",
    description=(
        "Returns a single product with its category, variants and linked images."
    ),
    response_description="The requested product.",
    responses={
        HTTP_STATUS_CODES.RESOURCE_NOT_FOUND.value: {
            "model": ErrorResponse,
            "description": "Product not found.",
        },
    },
)
async def get_product_controller(
    product_id: int = Path(ge=1, description="Id of the product to retrieve."),
    session: AsyncSession = Depends(get_db),
):
    product = await get_active_product_service(session, product_id)

    return ApiResponse[ProductResponse](
        message=HTTP_RESPONSE_MESSAGES.SUCCESS.value,
        data=ProductResponse.model_validate(product),
    )


@router.get(
    "/slug/{slug}",
    status_code=HTTP_STATUS_CODES.SUCCESS.value,
    response_model=ApiResponse[ProductResponse],
    summary="Get a product",
    description=(
        "Returns a single product with its category, variants and linked images."
    ),
    response_description="The requested product.",
    responses={
        HTTP_STATUS_CODES.RESOURCE_NOT_FOUND.value: {
            "model": ErrorResponse,
            "description": "Product not found.",
        },
    },
)
async def get_product_by_slug_controller(
    slug: str = Path(min_length=15, description="Slug of the product to retrieve."),
    session: AsyncSession = Depends(get_db),
):
    product = await get_active_product_by_slug_service(session, slug)

    return ApiResponse[ProductResponse](
        message=HTTP_RESPONSE_MESSAGES.SUCCESS.value,
        data=ProductResponse.model_validate(product),
    )
