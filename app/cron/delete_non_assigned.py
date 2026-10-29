import asyncio
import logging

from app.core.imagekit import imagekit_client
from app.db.session import SessionLocal
from app.repo.image import get_all_non_assigned_images_repo

logger = logging.getLogger(__name__)


async def delete_single_image(img, session):
    try:
        await imagekit_client.files.delete(img.file_id)
        await session.delete(img)
    except Exception as exc:
        logger.warning(f"Failed to delete {img.file_id} from ImageKit: {exc}")


async def delete_non_assigned_images_cron():
    logger.info("Starting unassigned images cleanup cron job...")

    async with SessionLocal() as session:
        try:
            non_assigned_images = await get_all_non_assigned_images_repo(session)

            if not non_assigned_images:
                logger.info("No unassigned images found to clean.")
                return

            semaphore = asyncio.Semaphore(5)

            async def sem_delete(img):
                async with semaphore:
                    await delete_single_image(img, session)

            await asyncio.gather(*(sem_delete(img) for img in non_assigned_images))

            await session.commit()
            logger.info(
                f"Successfully cleaned up {len(non_assigned_images)} orphaned images."
            )

        except Exception as e:
            await session.rollback()
            logger.exception(f"Error executing unassigned images cleanup cron: {e}")
