from imagekitio.types import FileUploadResponse
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.image import Image, ProductImage
from app.schemas.product import ProductImageInput


async def create_images_repo(
    session: AsyncSession, upload_responses: list[FileUploadResponse]
) -> list[Image]:
    images = [
        Image(
            file_id=response.file_id,
            url=response.url,
            file_path=response.file_path,
        )
        for response in upload_responses
    ]

    session.add_all(images)
    await session.flush()

    return images


async def create_image_repo(
    session: AsyncSession, upload_response: FileUploadResponse
) -> Image:
    image = Image(
        file_id=upload_response.file_id,
        url=upload_response.url,
        file_path=upload_response.file_path,
    )

    session.add(image)
    await session.flush()

    return image


async def get_images_by_ids_repo(
    session: AsyncSession, image_ids: list[int]
) -> list[Image]:
    stmt = select(Image).where(Image.id.in_(image_ids))
    return list(await session.scalars(stmt))


async def get_image_by_id_repo(session: AsyncSession, image_id: int) -> Image | None:
    stmt = select(Image).where(Image.id == image_id)
    return await session.scalar(stmt)


async def create_product_images_repo(
    session: AsyncSession,
    product_id: int,
    images_by_id: dict[int, Image],
    items: list[ProductImageInput],
) -> list[ProductImage]:
    product_images: list[ProductImage] = []

    for index, item in enumerate(items):
        product_images.append(
            ProductImage(
                image_id=images_by_id[item.image_id].id,
                product_id=product_id,
                display_order=index,
                is_primary=item.is_primary,
            )
        )

    session.add_all(product_images)
    await session.flush()

    return product_images


async def create_product_image_repo(
    session: AsyncSession,
    product_id: int,
    image_id: int,
    is_primary: bool = False,
) -> ProductImage:
    max_order = await get_max_display_order_repo(session, product_id)
    display_order = (max_order + 1) if max_order >= 0 else 0

    product_image = ProductImage(
        image_id=image_id,
        product_id=product_id,
        display_order=display_order,
        is_primary=is_primary,
    )

    session.add(product_image)
    await session.flush()

    return product_image


async def get_product_images_by_product_repo(session: AsyncSession, product_id: int):
    stmt = select(ProductImage).where(ProductImage.product_id == product_id)
    return list(await session.scalars(stmt))


async def count_product_images_repo(session: AsyncSession, product_id: int) -> int:
    stmt = (
        select(func.count())
        .select_from(ProductImage)
        .where(ProductImage.product_id == product_id)
    )
    return await session.scalar(stmt) or 0


async def get_lowest_order_product_image_repo(
    session: AsyncSession, product_id: int, exclude_id: int | None = None
):
    stmt = select(ProductImage).where(ProductImage.product_id == product_id)
    if exclude_id is not None:
        stmt = stmt.where(ProductImage.id != exclude_id)
    stmt = stmt.order_by(ProductImage.display_order).limit(1)
    return await session.scalar(stmt)


async def get_max_display_order_repo(session: AsyncSession, product_id: int):
    stmt = select(func.max(ProductImage.display_order)).where(
        ProductImage.product_id == product_id
    )

    max_order = await session.scalar(stmt)
    return max_order if max_order is not None else -1


async def get_product_image_by_id_repo(session: AsyncSession, product_image_id: int):
    stmt = (
        select(ProductImage)
        .where(ProductImage.id == product_image_id)
        .options(selectinload(ProductImage.image))
    )
    return await session.scalar(stmt)


async def delete_image_repo(session: AsyncSession, image: Image):
    await session.delete(image)
    await session.flush()


async def delete_product_image_repo(session: AsyncSession, product_image: ProductImage):
    await session.delete(product_image)
    await session.flush()


async def shift_product_images_repo(
    session: AsyncSession,
    product_id: int,
    from_display_order: int,
    by: int,
    to: int | None = None,
):
    """
    Excludes the from_display_order and to
    """
    filters = [
        ProductImage.product_id == product_id,
        ProductImage.display_order > from_display_order,
    ]

    if to is not None:
        filters.append(ProductImage.display_order < to)
    stmt = (
        update(ProductImage)
        .where(*filters)
        .values(display_order=ProductImage.display_order + by)
    )

    await session.execute(stmt)
    await session.flush()


async def unset_primary_image_repo(session: AsyncSession, product_id: int):
    stmt = (
        update(ProductImage)
        .where(ProductImage.product_id == product_id, ProductImage.is_primary == True)
        .values(is_primary=False)
    )
    await session.execute(stmt)
