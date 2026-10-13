from imagekitio.types import FileUploadResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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


async def get_images_by_ids_repo(
    session: AsyncSession, image_ids: list[int]
) -> list[Image]:
    stmt = select(Image).where(Image.id.in_(image_ids))
    return list(await session.scalars(stmt))


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
                display_order=item.display_order if item.display_order is not None else index,
                is_primary=item.is_primary,
            )
        )

    session.add_all(product_images)
    await session.flush()

    return product_images
