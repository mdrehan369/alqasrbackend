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
    get_image_by_id_repo,
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
    get_full_product_by_slug_repo,
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
    ProductsListFilters,
    UpdateProductImageRequest,
    UpdateProductRequest,
    UpdateProductVariantRequest,
)
from app.services.image import delete_imagekit_file
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

    for img in images:
        if img.is_assigned:
            raise BadRequestError(
                f"Image with url ${img.url} is already assigned to other entity"
            )

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
        for key, val in images_by_id.items():
            val.is_assigned = True
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    created = await get_full_product_by_id_repo(session, product.id)
    assert created is not None
    return created


async def get_products_service(
    session: AsyncSession, page: int, limit: int, product_filters: ProductsListFilters
):
    result, total = await get_products_repo(session, page, limit, product_filters)
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
        title = data["title"]
        if title.strip() == "":
            raise BadRequestError("Product title cannot be blank")
        existing = await get_product_by_title_repo(session, title)
        if existing is not None and existing.id != product.id:
            raise ConflictError("Product with this title already exists")
        product.title = title

    if "ingredients" in data:
        if data["ingredients"].strip() == "":
            raise BadRequestError("Product ingredients cannot be blank")
        product.ingredients = data["ingredients"]

    if "details" in data:
        if data["details"].strip() == "":
            raise BadRequestError("Product details cannot be blank")
        product.details = data["details"]

    if "is_active" in data:
        product.is_active = data["is_active"]

    if "category_id" in data:
        category = await get_category_by_id_repo(session, data["category_id"])
        if category is None:
            raise ResourceNotFoundError("Category not found")
        product.category_id = data["category_id"]

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise ConflictError("Product with this title already exists")

    await session.refresh(product)
    full = await get_full_product_by_id_repo(session, product.id)
    assert full is not None
    return full


async def delete_product_service(session: AsyncSession, product_id: int):
    product = await get_product_by_id_repo(session, product_id)
    if product is None:
        raise ResourceNotFoundError("Product not found")

    try:
        await session.delete(product)
        await session.commit()
    except Exception:
        await session.rollback()
        raise


async def create_product_variant_service(
    session: AsyncSession, product_id: int, payload: CreateProductVariantRequest
):
    product = await get_product_by_id_repo(session, product_id)
    if product is None:
        raise ResourceNotFoundError("Product not found")

    if payload.compare_price < payload.price:
        raise BadRequestError("compare_price must be greater than or equal to price")

    existing = await get_product_variant_by_combo_repo(
        session, product_id, payload.size, payload.unit, payload.product_type
    )
    if existing is not None:
        raise ConflictError(
            "Product variant with this size/unit/type already exists for this product"
        )

    try:
        variant = await create_product_variant_repo(session, product_id, payload)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise ConflictError(
            "Product variant with this size/unit/type already exists for this product"
        )
    except Exception:
        await session.rollback()
        raise

    await session.refresh(variant)
    return variant


async def update_product_variant_service(
    session: AsyncSession,
    product_id: int,
    variant_id: int,
    payload: UpdateProductVariantRequest,
):
    product = await get_product_by_id_repo(session, product_id)
    if product is None:
        raise ResourceNotFoundError("Product not found")

    variant = await get_product_variant_by_id_and_product_repo(
        session, variant_id, product_id
    )
    if variant is None:
        raise ResourceNotFoundError("Product variant not found")

    data = payload.model_dump(exclude_unset=True)
    data = {key: value for key, value in data.items() if value is not None}

    merged_size = data.get("size", variant.size)
    merged_unit = data.get("unit", variant.unit)
    merged_type = data.get("product_type", variant.product_type)
    merged_price = data.get("price", variant.price)
    merged_compare = data.get("compare_price", variant.compare_price)

    if merged_size <= 0:
        raise BadRequestError("size must be greater than 0")
    if merged_price < 0:
        raise BadRequestError("price must be greater than or equal to 0")
    if merged_compare < 0:
        raise BadRequestError("compare_price must be greater than or equal to 0")
    if merged_compare < merged_price:
        raise BadRequestError("compare_price must be greater than or equal to price")

    if "size" in data and data["size"] <= 0:
        raise BadRequestError("size must be greater than 0")
    if "price" in data and data["price"] < 0:
        raise BadRequestError("price must be greater than or equal to 0")
    if "compare_price" in data and data["compare_price"] < 0:
        raise BadRequestError("compare_price must be greater than or equal to 0")
    if "stock" in data and data["stock"] < 0:
        raise BadRequestError("stock must be greater than or equal to 0")

    if "size" in data or "unit" in data or "product_type" in data:
        existing = await get_product_variant_by_combo_repo(
            session,
            product_id,
            merged_size,
            merged_unit,
            merged_type,
            exclude_id=variant_id,
        )
        if existing is not None:
            raise ConflictError(
                "Product variant with this size/unit/type already exists for this product"
            )

    if "size" in data:
        variant.size = data["size"]
    if "unit" in data:
        variant.unit = data["unit"]
    if "product_type" in data:
        variant.product_type = data["product_type"]
    if "stock" in data:
        variant.stock = data["stock"]
    if "price" in data:
        variant.price = data["price"]
    if "compare_price" in data:
        variant.compare_price = data["compare_price"]

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise ConflictError(
            "Product variant with this size/unit/type already exists for this product"
        )
    except Exception:
        await session.rollback()
        raise

    await session.refresh(variant)
    return variant


async def delete_product_variant_service(
    session: AsyncSession, product_id: int, variant_id: int
):
    product = await get_product_by_id_repo(session, product_id)
    if product is None:
        raise ResourceNotFoundError("Product not found")

    variant = await get_product_variant_by_id_and_product_repo(
        session, variant_id, product_id
    )
    if variant is None:
        raise ResourceNotFoundError("Product variant not found")

    variants = await get_product_variants_by_product_repo(session, product_id)
    if len(variants) <= 1:
        raise CannotDeleteError("Cannot delete the last variant of a product")

    try:
        await delete_product_variant_repo(session, variant)
        await session.commit()
    except Exception:
        await session.rollback()
        raise


async def add_product_image_service(
    session: AsyncSession,
    product_id: int,
    image_id: int,
    commit: bool = True,
):
    product = await get_product_by_id_repo(session, product_id)
    if product is None:
        raise ResourceNotFoundError("Product not found")

    count = await count_product_images_repo(session, product_id)
    if count >= MAX_IMAGES_PER_PRODUCT:
        raise BadRequestError(
            f"Maximum {MAX_IMAGES_PER_PRODUCT} images allowed per product"
        )

    image = await get_image_by_id_repo(session, image_id)
    if not image:
        raise ResourceNotFoundError("Image not found")

    if image.is_assigned:
        raise BadRequestError("This image is already assigned to some other entity")

    try:
        created = await create_product_image_repo(session, product_id, image_id, False)
        image.is_assigned = True
        if commit:
            await session.commit()
    except IntegrityError:
        await session.rollback()
        raise ConflictError("Image already linked to product")
    except Exception:
        await session.rollback()
        raise

    try:
        await session.refresh(created, attribute_names=["image"])
    except Exception:
        pass
    return created


async def update_product_image_service(
    session: AsyncSession,
    product_id: int,
    product_image_id: int,
    payload: UpdateProductImageRequest,
):
    product = await get_product_by_id_repo(session, product_id)
    if product is None:
        raise ResourceNotFoundError("Product not found")

    link = await get_product_image_by_id_repo(session, product_image_id)
    if link is None:
        raise ResourceNotFoundError("Product image not found")

    if link.product_id != product_id:
        raise BadRequestError("This image does not belongs to this product")

    data = payload.model_dump(exclude_unset=True)

    new_primary = data.get("is_primary")
    new_order = data.get("display_order")

    if new_primary == False and len(data) == 1:
        raise BadRequestError("Cannot unset primary status")

    if new_primary == False and link.is_primary == False:
        raise BadRequestError("The image is already not a primary image")

    if new_primary is True:
        await unset_primary_image_repo(session, product_id)

    if new_order is not None:
        max_order = await get_max_display_order_repo(session, product_id)
        new_order = min(new_order, max_order)

        if new_order < link.display_order:
            await shift_product_images_repo(
                session, product_id, new_order - 1, +1, link.display_order
            )
        elif new_order > link.display_order:
            await shift_product_images_repo(
                session, product_id, link.display_order, -1, new_order + 1
            )
        link.display_order = new_order

    if new_primary is True:
        link.is_primary = True
    elif new_primary is False and link.is_primary:
        raise BadRequestError("Cannot unset primary status")

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    await session.refresh(link)
    try:
        await session.refresh(link, attribute_names=["image"])
    except Exception:
        pass
    return link


async def delete_product_image_service(
    session: AsyncSession,
    product_id: int,
    product_image_id: int,
    commit: bool = True,
):
    """
    If commit is set to false, be sure to delete the imagekit file as this function only deletes it when its set to true
    """
    product = await get_product_by_id_repo(session, product_id)
    if product is None:
        raise ResourceNotFoundError("Product not found")

    link = await get_product_image_by_id_repo(session, product_image_id)
    if link is None:
        raise ResourceNotFoundError("Product image not found")

    if link.product_id != product_id:
        raise BadRequestError("This image does not belongs to this product")

    product_images_count = await count_product_images_repo(session, product_id)
    if product_images_count == 1:
        raise CannotDeleteError("This is the last image, it cannot be deleted")

    was_primary = link.is_primary
    image = link.image

    if image is None:
        raise BadRequestError("No image found!")

    try:
        await session.delete(link)
        await delete_image_repo(session, image)
        if was_primary:
            lowest = await get_lowest_order_product_image_repo(session, product_id)
            if lowest is not None:
                lowest.is_primary = True
        await shift_product_images_repo(session, product_id, link.display_order, -1)
        if commit:
            await session.commit()
    except Exception:
        await session.rollback()
        print("Some error occured while deleting the imagekit file!")
        raise

    try:
        if commit:
            await delete_imagekit_file(image.file_id)
    except Exception:
        print("Imagekit deletion failed!")


async def get_product_by_slug_service(session: AsyncSession, slug: str):
    product = await get_full_product_by_slug_repo(session, slug)
    if product is None:
        raise ResourceNotFoundError("Product not found")

    return product
