import math

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api_response import ApiResponse, ErrorResponse
from app.db.session import get_db
from app.schemas.pagination import PaginatedResponse, Pagination
from app.schemas.product import (
    CreateProductRequest,
    CreateProductVariantRequest,
    OnlyProductResponse,
    ProductResponse,
    ProductVariantResponse,
    UpdateProductRequest,
    UpdateProductVariantRequest,
)
from app.services.product import (
    create_product_service,
    create_product_variant_service,
    delete_product_variant_service,
    get_product_service,
    get_products_service,
    update_product_service,
    update_product_variant_service,
)
from app.utils.constants import HTTP_RESPONSE_MESSAGES, HTTP_STATUS_CODES

router = APIRouter(tags=["Product"])


@router.post(
    "/",
    status_code=HTTP_STATUS_CODES.CREATED.value,
    response_model=ApiResponse[ProductResponse],
    summary="Create a product",
    description=(
        "Creates a product with its variants and links to previously uploaded "
        "images. Upload images first via POST /api/v1/admin/images."
    ),
    response_description="The created product with its variants and images.",
    responses={
        HTTP_STATUS_CODES.CONFLICT.value: {
            "model": ErrorResponse,
            "description": "A product with the same title already exists.",
        },
        HTTP_STATUS_CODES.RESOURCE_NOT_FOUND.value: {
            "model": ErrorResponse,
            "description": "Category or one of the referenced images was not found.",
        },
    },
)
async def create_product_controller(
    payload: CreateProductRequest,
    session: AsyncSession = Depends(get_db),
):
    product = await create_product_service(session, payload)

    return ApiResponse[ProductResponse](
        message=HTTP_RESPONSE_MESSAGES.CREATED.value,
        data=ProductResponse.model_validate(product),
    )


@router.get(
    "/",
    status_code=HTTP_STATUS_CODES.SUCCESS.value,
    response_model=ApiResponse[PaginatedResponse[ProductResponse]],
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
        default="", max_length=100, description="Case-insensitive name prefix filter."
    ),
):
    result, total = await get_products_service(session, page, limit, search)
    total_pages = math.ceil(total / limit) if total else 0

    return ApiResponse[PaginatedResponse[ProductResponse]](
        data=PaginatedResponse(
            items=[ProductResponse.model_validate(c) for c in result],
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
            "description": "No product exists with the given id.",
        },
    },
)
async def get_product_controller(
    product_id: int = Path(ge=1, description="Id of the product to fetch."),
    session: AsyncSession = Depends(get_db),
):
    product = await get_product_service(session, product_id)

    return ApiResponse[ProductResponse](
        message=HTTP_RESPONSE_MESSAGES.SUCCESS.value,
        data=ProductResponse.model_validate(product),
    )


@router.patch(
    "/{product_id}",
    status_code=HTTP_STATUS_CODES.SUCCESS.value,
    response_model=ApiResponse[OnlyProductResponse],
    summary="Update a product",
    description=(
        "Partially updates a product's own fields (title, ingredients, details, "
        "activation state and category). Omitted fields are left unchanged. "
        "Variants and images are managed via their own endpoints."
    ),
    response_description="The updated product.",
    responses={
        HTTP_STATUS_CODES.BAD_REQUEST.value: {
            "model": ErrorResponse,
            "description": "The provided title is blank.",
        },
        HTTP_STATUS_CODES.RESOURCE_NOT_FOUND.value: {
            "model": ErrorResponse,
            "description": "Product or category not found.",
        },
        HTTP_STATUS_CODES.CONFLICT.value: {
            "model": ErrorResponse,
            "description": "A product with the same title already exists.",
        },
    },
)
async def update_product_controller(
    payload: UpdateProductRequest,
    product_id: int = Path(ge=1, description="Id of the product to update."),
    session: AsyncSession = Depends(get_db),
):
    updated_product = await update_product_service(session, product_id, payload)
    return ApiResponse[OnlyProductResponse](
        message=HTTP_RESPONSE_MESSAGES.UPDATED.value,
        data=OnlyProductResponse.model_validate(updated_product),
    )


@router.post(
    "/{product_id}/variants",
    status_code=HTTP_STATUS_CODES.CREATED.value,
    response_model=ApiResponse[ProductVariantResponse],
    summary="Create a product variant",
    description=(
        "Adds a new variant (size, unit, type, price, compare price, stock) to an "
        "existing product. The size/unit/type combination must be unique per product."
    ),
    response_description="The created product variant.",
    responses={
        HTTP_STATUS_CODES.RESOURCE_NOT_FOUND.value: {
            "model": ErrorResponse,
            "description": "No product exists with the given id.",
        },
        HTTP_STATUS_CODES.CONFLICT.value: {
            "model": ErrorResponse,
            "description": "A variant with the same size, unit and type already exists.",
        },
    },
)
async def create_product_variant_controller(
    payload: CreateProductVariantRequest,
    product_id: int = Path(ge=1, description="Id of the parent product."),
    session: AsyncSession = Depends(get_db),
):
    variant = await create_product_variant_service(session, product_id, payload)
    return ApiResponse[ProductVariantResponse](
        message=HTTP_RESPONSE_MESSAGES.CREATED.value,
        data=ProductVariantResponse.model_validate(variant),
    )


@router.patch(
    "/{product_id}/variants/{variant_id}",
    status_code=HTTP_STATUS_CODES.SUCCESS.value,
    response_model=ApiResponse[ProductVariantResponse],
    summary="Update a product variant",
    description=(
        "Partially updates a variant belonging to the given product. Omitted "
        "fields are left unchanged. The resulting size/unit/type combination must "
        "remain unique per product, and compare_price must stay >= price."
    ),
    response_description="The updated product variant.",
    responses={
        HTTP_STATUS_CODES.BAD_REQUEST.value: {
            "model": ErrorResponse,
            "description": (
                "The resulting values are invalid (negative numbers or "
                "compare_price lower than price)."
            ),
        },
        HTTP_STATUS_CODES.RESOURCE_NOT_FOUND.value: {
            "model": ErrorResponse,
            "description": "The product or variant could not be found.",
        },
        HTTP_STATUS_CODES.CONFLICT.value: {
            "model": ErrorResponse,
            "description": "Another variant already uses this size, unit and type.",
        },
    },
)
async def update_product_variant_controller(
    payload: UpdateProductVariantRequest,
    product_id: int = Path(ge=1, description="Id of the parent product."),
    variant_id: int = Path(ge=1, description="Id of the variant to update."),
    session: AsyncSession = Depends(get_db),
):
    updated_variant = await update_product_variant_service(
        session, product_id, variant_id, payload
    )
    return ApiResponse[ProductVariantResponse](
        message=HTTP_RESPONSE_MESSAGES.UPDATED.value,
        data=ProductVariantResponse.model_validate(updated_variant),
    )


@router.delete(
    "/{product_id}/variants/{variant_id}",
    status_code=HTTP_STATUS_CODES.NO_CONTENT.value,
    summary="Delete a product variant",
    description=(
        "Deletes a variant belonging to the given product. The last remaining "
        "variant of a product cannot be deleted."
    ),
    responses={
        HTTP_STATUS_CODES.BAD_REQUEST.value: {
            "model": ErrorResponse,
            "description": "The variant is the last one and cannot be deleted.",
        },
        HTTP_STATUS_CODES.RESOURCE_NOT_FOUND.value: {
            "model": ErrorResponse,
            "description": "The product or variant could not be found.",
        },
    },
)
async def delete_product_variant_controller(
    product_id: int = Path(ge=1, description="Id of the parent product."),
    variant_id: int = Path(ge=1, description="Id of the variant to delete."),
    session: AsyncSession = Depends(get_db),
):
    await delete_product_variant_service(session, product_id, variant_id)
