import math

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api_response import ApiResponse, ErrorResponse
from app.db.models.product import ProductType
from app.db.session import get_db
from app.schemas.pagination import PaginatedResponse, Pagination
from app.schemas.product import (
    ProductListItemClientResponse,
    ProductResponse,
    ProductsListFiltersClient,
    SortBy,
    SortOrder,
)
from app.services.product import (
    get_active_product_by_slug_service,
    get_active_product_service,
    get_products_for_client_service,
)
from app.utils.constants import HTTP_RESPONSE_MESSAGES, HTTP_STATUS_CODES

router = APIRouter(tags=["Product"])


@router.get(
    "/",
    status_code=HTTP_STATUS_CODES.SUCCESS.value,
    response_model=ApiResponse[PaginatedResponse[ProductListItemClientResponse]],
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
        default="", max_length=100, description="Case-insensitive prefix filter."
    ),
    category_ids: list[int] = Query(
        default=[], description="The categories to search for"
    ),
    sort_order: SortOrder = Query(
        default=SortOrder.ASC,
        description="The sort order for the field created_at",
    ),
    sort_by: SortBy = Query(
        default=SortBy.CREATED_AT,
        description="The sort by field for the query",
    ),
    product_types: list[ProductType] = Query(
        default=[ProductType.AATR, ProductType.PERFUME],
        description="The product types included",
    ),
):
    product_filters = ProductsListFiltersClient(
        sort_order=sort_order,
        search=search,
        category_ids=category_ids,
        sort_by=sort_by,
        product_types=product_types,
    )
    results, total = await get_products_for_client_service(
        session, page, limit, product_filters
    )
    total_pages = math.ceil(total / limit) if total else 0

    return ApiResponse[PaginatedResponse[ProductListItemClientResponse]](
        data=PaginatedResponse(
            items=[ProductListItemClientResponse.model_validate(c) for c in results],
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
