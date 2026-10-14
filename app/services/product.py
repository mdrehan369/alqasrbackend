from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BadRequestError,
    CannotDeleteError,
    ConflictError,
    ResourceNotFoundError,
)
from app.repo.category import get_category_by_id_repo
from app.repo.image import (
    count_product_images_repo,
    create_product_image_repo,
    create_product_images_repo,
    delete_image_repo,
    delete_product_image_repo,
    get_images_by_ids_repo,
    get_lowest_order_product_image_repo,
    get_max_display_order_repo,
    get_product_image_by_id_repo,
    shift_product_images_repo,
    unset_primary_image_repo,
)
from app.repo.product import (
    create_product_repo,
    create_product_variant_repo,
    create_product_variants_repo,
    delete_product_variant_repo,
    get_full_product_by_id_repo,
    get_product_by_id_repo,
    get_product_by_title_repo,
    get_product_variant_by_combo_repo,
    get_product_variant_by_id_and_product_repo,
    get_product_variants_by_product_repo,
    get_products_repo,
)
from app.schemas.product import (
    CreateProductRequest,
    CreateProductVariantRequest,
    UpdateProductImageRequest,
    UpdateProductRequest,
    UpdateProductVariantRequest,
)
from app.services.image import delete_imagekit_file, upload_image_service
from app.utils.constants import MAX_IMAGES_PER_PRODUCT


async def create_product_service(session: AsyncSession, payload: CreateProductRequest):
    if await get_product_by_title_repo(session, payload.title) is not None:
        raise ConflictError("Product with this title already exists")

    if await get_category_by_id_repo(session, payload.category_id) is None:
        raise ResourceNotFoundError("Category not found")

    if not any(item.is_primary for item in payload.images):
        payload.images[0].is_primary = True

    requested_image_ids = [item.image_id for item in payload.images]
    images = await get_images_by_ids_repo(session, requested_image_ids)
    images_by_id = {image.id: image for image in images}

    missing_image_ids = set(requested_image_ids) - set(images_by_id)
    if missing_image_ids:
        raise ResourceNotFoundError(f"Images not found: {sorted(missing_image_ids)}")

    payload.images.sort(key=lambda img: img.display_order or 0)

    try:
        product = await create_product_repo(session, payload)
        await create_product_variants_repo(session, product.id, payload.variants)
        await create_product_images_repo(
            session, product.id, images_by_id, payload.images
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    created = await get_full_product_by_id_repo(session, product.id)
    assert created is not None
    return created


async def get_products_service(
    session: AsyncSession, page: int, limit: int, search: str
):
    result, total = await get_products_repo(session, page, limit, search)
    return result, total


async def get_product_service(session: AsyncSession, product_id: int):
    product = await get_full_product_by_id_repo(session, product_id)
    if product is None:
        raise ResourceNotFoundError("Product not found")

    return product


async def update_product_service(
    session: AsyncSession, product_id: int, payload: UpdateProductRequest
):
    product = await get_product_by_id_repo(session, product_id)
    if product is None:
        raise ResourceNotFoundError("Product not found")

    data = payload.model_dump(exclude_unset=True)
    data = {key: value for key, value in data.items() if value is not None}

    if "title" in data:
        new_title = data["title"]
        if not new_title.strip():
            raise BadRequestError("Product title cannot be blank")

        if new_title.lower() != product.title.lower():
            product_with_new_title = await get_product_by_title_repo(session, new_title)
            if product_with_new_title is not None:
                raise ConflictError("Product with this title already exists")

            product.title = new_title

    if "category_id" in data:
        new_category_id = data["category_id"]
        if new_category_id != product.category_id:
            cat = await get_category_by_id_repo(session, new_category_id)
            if cat is None:
                raise ResourceNotFoundError("Category not found")

            product.category_id = new_category_id

    if "ingredients" in data:
        product.ingredients = data["ingredients"]

    if "details" in data:
        product.details = data["details"]

    if "is_active" in data:
        product.is_active = data["is_active"]

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise ConflictError("Product update conflicts with existing data") from None

    await session.refresh(product)

    return product


async def create_product_variant_service(
    session: AsyncSession, product_id: int, payload: CreateProductVariantRequest
):
    product = await get_product_by_id_repo(session, product_id)
    if product is None:
        raise ResourceNotFoundError("Product not found")

    existing = await get_product_variant_by_combo_repo(
        session, product_id, payload.size, payload.unit, payload.product_type
    )
    if existing is not None:
        raise ConflictError(
            "Product variant with this size, unit and type already exists"
        )

    variant = await create_product_variant_repo(session, product_id, payload)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise ConflictError(
            "Product variant with this size, unit and type already exists"
        ) from None

    await session.refresh(variant)

    return variant


async def update_product_variant_service(
    session: AsyncSession,
    product_id: int,
    variant_id: int,
    payload: UpdateProductVariantRequest,
):
    variant = await get_product_variant_by_id_and_product_repo(
        session, variant_id, product_id
    )
    if variant is None:
        raise ResourceNotFoundError("Product variant not found")

    data = payload.model_dump(exclude_unset=True)
    data = {key: value for key, value in data.items() if value is not None}

    merged_size = data.get("size", variant.size)
    merged_unit = data.get("unit", variant.unit)
    merged_product_type = data.get("product_type", variant.product_type)
    merged_price = data.get("price", variant.price)
    merged_compare_price = data.get("compare_price", variant.compare_price)
    merged_stock = data.get("stock", variant.stock)

    if (
        merged_size <= 0
        or merged_price < 0
        or merged_compare_price < 0
        or merged_stock < 0
    ):
        raise BadRequestError(
            "size must be greater than 0 and price, compare_price and stock "
            "must be greater than or equal to 0"
        )

    if merged_compare_price < merged_price:
        raise BadRequestError("compare_price must be greater than or equal to price")

    existing = await get_product_variant_by_combo_repo(
        session,
        product_id,
        merged_size,
        merged_unit,
        merged_product_type,
        exclude_id=variant.id,
    )
    if existing is not None:
        raise ConflictError(
            "Product variant with this size, unit and type already exists"
        )

    for key, value in data.items():
        variant.__setattr__(key, value)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise ConflictError(
            "Product variant with this size, unit and type already exists"
        ) from None

    await session.refresh(variant)

    return variant


async def delete_product_variant_service(
    session: AsyncSession, product_id: int, variant_id: int
):
    variant = await get_product_variant_by_id_and_product_repo(
        session, variant_id, product_id
    )
    if variant is None:
        raise ResourceNotFoundError("Product variant not found")

    all_variants = await get_product_variants_by_product_repo(session, product_id)

    if len(all_variants) == 1:
        raise CannotDeleteError(
            "This is the last variant in the product. Add another variant and then delete this"
        )

    await delete_product_variant_repo(session, variant)
    await session.commit()


async def add_product_image_service(
    session: AsyncSession, product_id: int, file: UploadFile
):
    product = await get_product_by_id_repo(session, product_id)
    if product is None:
        raise ResourceNotFoundError("Product not found")

    image_count = await count_product_images_repo(session, product_id)
    if image_count >= MAX_IMAGES_PER_PRODUCT:
        raise BadRequestError(
            f"A product can have at most {MAX_IMAGES_PER_PRODUCT} images"
        )

    image = await upload_image_service(session, file, commit=False)
    file_id = image.file_id

    try:
        display_order = (await get_max_display_order_repo(session, product_id)) + 1
        product_image = await create_product_image_repo(
            session,
            product_id,
            image,
            display_order,
            is_primary=image_count == 0,
        )

        await session.commit()
    except Exception:
        await session.rollback()
        await delete_imagekit_file(file_id)
        raise

    refreshed = await get_product_image_by_id_repo(session, product_image.id)
    assert refreshed is not None
    return refreshed


async def delete_product_image_service(
    session: AsyncSession, product_id: int, product_image_id: int
):
    product = await get_product_by_id_repo(session, product_id)
    if product is None:
        raise ResourceNotFoundError("Product not found")

    product_image = await get_product_image_by_id_repo(session, product_image_id)
    if product_image is None:
        raise ResourceNotFoundError("Product image not found")

    if product_image.product_id != product_id:
        raise BadRequestError("This image does not belong to this product")

    promote = None
    if product_image.is_primary:
        promote = await get_lowest_order_product_image_repo(
            session, product_id, product_image.id
        )

    try:
        await delete_imagekit_file(product_image.image.file_id)
        await delete_product_image_repo(session, product_image)
        await session.flush()
        await delete_image_repo(session, product_image.image)
        await shift_product_images_repo(
            session, product_id, product_image.display_order, -1
        )
        if promote is not None:
            promote.is_primary = True
        await session.commit()
    except Exception:
        await session.rollback()
        raise


async def update_product_image_service(
    session: AsyncSession,
    product_id: int,
    product_image_id: int,
    payload: UpdateProductImageRequest,
):
    product = await get_product_by_id_repo(session, product_id)
    if product is None:
        raise ResourceNotFoundError("Product not found")

    product_image = await get_product_image_by_id_repo(session, product_image_id)
    if product_image is None:
        raise ResourceNotFoundError("Product image not found")

    if product_image.product_id != product_id:
        raise BadRequestError("This image does not belong to this product")

    data = payload.model_dump(exclude_unset=True)
    data = {key: value for key, value in data.items() if value is not None}

    try:
        if "is_primary" in data:
            if data["is_primary"]:
                await unset_primary_image_repo(session, product_id)
                product_image.is_primary = True
            elif product_image.is_primary:
                raise BadRequestError("First make some other image primary")

        if (
            "display_order" in data
            and product_image.display_order != data["display_order"]
        ):
            max_order = await get_max_display_order_repo(session, product_id)
            new_order = data["display_order"]
            prev_order = product_image.display_order

            if new_order > max_order:
                raise BadRequestError("New display order is greater than the max order")

            if new_order < prev_order:
                await shift_product_images_repo(
                    session, product_id, new_order - 1, 1, prev_order - 1
                )
            else:
                await shift_product_images_repo(
                    session, product_id, prev_order, -1, new_order
                )

            product_image.display_order = new_order

        await session.commit()
    except Exception:
        await session.rollback()
        raise

    refreshed = await get_product_image_by_id_repo(session, product_image.id)
    assert refreshed is not None
    return refreshed
