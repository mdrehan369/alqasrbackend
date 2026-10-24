import math

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.v1.endpoints.auth import get_current_user_controller
from app.core.api_response import ApiResponse, ErrorResponse
from app.db.session import get_db
from app.schemas.pagination import PaginatedResponse, Pagination
from app.schemas.product import (
    CreateProductRequest,
    CreateProductVariantRequest,
    ProductImageResponse,
    ProductListItemResponse,
    ProductResponse,
    ProductsListFilters,
    ProductVariantResponse,
    SearchableProductFields,
    SortOrder,
    UpdateProductImageRequest,
    UpdateProductRequest,
    UpdateProductVariantRequest,
)
from app.services.product import (
    add_product_image_service,
    create_product_service,
    create_product_variant_service,
    delete_product_image_service,
    delete_product_service,
    delete_product_variant_service,
    get_product_service,
    get_products_service,
    update_product_image_service,
    update_product_service,
    update_product_variant_service,
)
from app.utils.constants import HTTP_RESPONSE_MESSAGES, HTTP_STATUS_CODES

router = APIRouter(
    tags=["Product"], dependencies=[Depends(get_current_user_controller)]
)


@router.post(
    "/",
    status_code=HTTP_STATUS_CODES.CREATED.value,
    response_model=ApiResponse[ProductResponse],
    summary="Create a product",
    description=(
        "Creates a product with its variants and links to previously uploaded "
        "images. Upload images first via POST /api/v1/admin/images. If no primary image is selected, "
        "then the first uploaded image would be considered as primary. Also display order becomes consecutive"
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
    is_active: bool | None = Query(
        default=None, description="The value of the field of is_active"
    ),
):
    product_filters = ProductsListFilters(
        sort_order=sort_order,
        search=search,
        search_in=search_in,
        category_ids=category_ids,
        is_active=is_active,
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
    product = await get_product_service(session, product_id)

    return ApiResponse[ProductResponse](
        message=HTTP_RESPONSE_MESSAGES.SUCCESS.value,
        data=ProductResponse.model_validate(product),
    )


@router.patch(
    "/{product_id}",
    status_code=HTTP_STATUS_CODES.SUCCESS.value,
    response_model=ApiResponse[ProductResponse],
    summary="Update a product",
    description=(
        "Partially updates a product. Omitted or null fields are left unchanged; "
        "title and category_id are validated if provided."
    ),
    response_description="The updated product with its relations.",
    responses={
        HTTP_STATUS_CODES.RESOURCE_NOT_FOUND.value: {
            "model": ErrorResponse,
            "description": "Product or category not found.",
        },
        HTTP_STATUS_CODES.BAD_REQUEST.value: {
            "model": ErrorResponse,
            "description": "Product title cannot be blank.",
        },
        HTTP_STATUS_CODES.CONFLICT.value: {
            "model": ErrorResponse,
            "description": "Another product already uses that title.",
        },
    },
)
async def update_product_controller(
    payload: UpdateProductRequest,
    product_id: int = Path(ge=1, description="Id of the product to update."),
    session: AsyncSession = Depends(get_db),
):
    product = await update_product_service(session, product_id, payload)

    return ApiResponse[ProductResponse](
        message=HTTP_RESPONSE_MESSAGES.UPDATED.value,
        data=ProductResponse.model_validate(product),
    )


@router.delete(
    "/{product_id}",
    status_code=HTTP_STATUS_CODES.NO_CONTENT.value,
    summary="Delete a product",
    description="Deletes a product and its variants and linked product-image entries.",
    responses={
        HTTP_STATUS_CODES.RESOURCE_NOT_FOUND.value: {
            "model": ErrorResponse,
            "description": "Product not found.",
        },
    },
)
async def delete_product_controller(
    product_id: int = Path(ge=1, description="Id of the product to delete."),
    session: AsyncSession = Depends(get_db),
):
    await delete_product_service(session, product_id)


@router.post(
    "/{product_id}/variants",
    status_code=HTTP_STATUS_CODES.CREATED.value,
    response_model=ApiResponse[ProductVariantResponse],
    summary="Create a product variant",
    description="Adds a variant to an existing product. Validates the full combination for duplicates.",
    response_description="The created variant.",
    responses={
        HTTP_STATUS_CODES.RESOURCE_NOT_FOUND.value: {
            "model": ErrorResponse,
            "description": "Product not found.",
        },
        HTTP_STATUS_CODES.BAD_REQUEST.value: {
            "model": ErrorResponse,
            "description": "Price/compare_price or size values are invalid.",
        },
        HTTP_STATUS_CODES.CONFLICT.value: {
            "model": ErrorResponse,
            "description": "A variant with the same size/unit/type already exists for this product.",
        },
    },
)
async def create_product_variant_controller(
    payload: CreateProductVariantRequest,
    product_id: int = Path(ge=1, description="Id of the product to add a variant to."),
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
        "Partially updates a variant. Only the supplied fields change and the merged "
        "values are validated (e.g. compare_price >= price)."
    ),
    response_description="The updated variant.",
    responses={
        HTTP_STATUS_CODES.RESOURCE_NOT_FOUND.value: {
            "model": ErrorResponse,
            "description": "Product or variant not found.",
        },
        HTTP_STATUS_CODES.BAD_REQUEST.value: {
            "model": ErrorResponse,
            "description": "Price/compare_price or size values are invalid.",
        },
        HTTP_STATUS_CODES.CONFLICT.value: {
            "model": ErrorResponse,
            "description": "Another variant with the same size/unit/type already exists for this product.",
        },
    },
)
async def update_product_variant_controller(
    payload: UpdateProductVariantRequest,
    product_id: int = Path(
        ge=1, description="Id of the product that owns the variant."
    ),
    variant_id: int = Path(ge=1, description="Id of the variant to update."),
    session: AsyncSession = Depends(get_db),
):
    variant = await update_product_variant_service(
        session, product_id, variant_id, payload
    )

    return ApiResponse[ProductVariantResponse](
        message=HTTP_RESPONSE_MESSAGES.UPDATED.value,
        data=ProductVariantResponse.model_validate(variant),
    )


@router.delete(
    "/{product_id}/variants/{variant_id}",
    status_code=HTTP_STATUS_CODES.NO_CONTENT.value,
    summary="Delete a product variant",
    description="Deletes a variant. The product must keep at least one variant.",
    responses={
        HTTP_STATUS_CODES.RESOURCE_NOT_FOUND.value: {
            "model": ErrorResponse,
            "description": "Product or variant not found.",
        },
        HTTP_STATUS_CODES.BAD_REQUEST.value: {
            "model": ErrorResponse,
            "description": "Cannot delete the last variant of a product.",
        },
    },
)
async def delete_product_variant_controller(
    product_id: int = Path(
        ge=1, description="Id of the product that owns the variant."
    ),
    variant_id: int = Path(ge=1, description="Id of the variant to delete."),
    session: AsyncSession = Depends(get_db),
):
    await delete_product_variant_service(session, product_id, variant_id)


@router.post(
    "/{product_id}/images/{image_id}",
    status_code=HTTP_STATUS_CODES.CREATED.value,
    response_model=ApiResponse[ProductImageResponse],
    summary="Add an image to a product",
    description=(
        "Links an already uploaded image to the product. "
        "Only 10 images per product are allowed."
    ),
    response_description="The created product-image link.",
    responses={
        HTTP_STATUS_CODES.RESOURCE_NOT_FOUND.value: {
            "model": ErrorResponse,
            "description": "Product or image not found.",
        },
        HTTP_STATUS_CODES.BAD_REQUEST.value: {
            "model": ErrorResponse,
            "description": "Image limit exceeded or invalid file/reference.",
        },
    },
)
async def add_product_image_controller(
    product_id: int = Path(ge=1, description="Id of the product to link the image to."),
    image_id: int = Path(ge=1, description="Id of the uploaded image to link."),
    session: AsyncSession = Depends(get_db),
):
    product_image = await add_product_image_service(session, product_id, image_id)

    return ApiResponse[ProductImageResponse](
        message=HTTP_RESPONSE_MESSAGES.CREATED.value,
        data=ProductImageResponse.model_validate(product_image),
    )


@router.patch(
    "/{product_id}/images/{product_image_id}",
    status_code=HTTP_STATUS_CODES.SUCCESS.value,
    response_model=ApiResponse[ProductImageResponse],
    summary="Update a product image",
    description="Set a cover image or reorder it within the gallery.",
    response_description="The updated product-image link.",
    responses={
        HTTP_STATUS_CODES.RESOURCE_NOT_FOUND.value: {
            "model": ErrorResponse,
            "description": "Product or product-image link not found.",
        },
        HTTP_STATUS_CODES.BAD_REQUEST.value: {
            "model": ErrorResponse,
            "description": "Invalid ordering or payload.",
        },
        HTTP_STATUS_CODES.UNPROCESSABLE_ENTITY.value: {
            "model": ErrorResponse,
            "description": "Payload must include at least one updatable field.",
        },
    },
)
async def update_product_image_controller(
    payload: UpdateProductImageRequest,
    product_id: int = Path(ge=1, description="Id of the product that owns the image."),
    product_image_id: int = Path(
        ge=1, description="Id of the product-image link to update."
    ),
    session: AsyncSession = Depends(get_db),
):
    product_image = await update_product_image_service(
        session, product_id, product_image_id, payload
    )

    return ApiResponse[ProductImageResponse](
        message=HTTP_RESPONSE_MESSAGES.UPDATED.value,
        data=ProductImageResponse.model_validate(product_image),
    )


@router.delete(
    "/{product_id}/images/{product_image_id}",
    status_code=HTTP_STATUS_CODES.NO_CONTENT.value,
    summary="Remove an image from a product",
    description=(
        "Unlinks the image from the product. If the primary image is removed, the "
        "next image becomes primary automatically."
    ),
    responses={
        HTTP_STATUS_CODES.RESOURCE_NOT_FOUND.value: {
            "model": ErrorResponse,
            "description": "Product or product-image link not found.",
        },
    },
)
async def delete_product_image_controller(
    product_id: int = Path(ge=1, description="Id of the product that owns the image."),
    product_image_id: int = Path(
        ge=1, description="Id of the product-image link to delete."
    ),
    session: AsyncSession = Depends(get_db),
):
    await delete_product_image_service(session, product_id, product_image_id)
