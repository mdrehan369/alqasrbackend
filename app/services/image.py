import logging
from pathlib import Path

from fastapi import UploadFile
from imagekitio.types import FileUploadResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import FileUploadError, InvalidFileError
from app.core.imagekit import imagekit_client
from app.db.models.image import Image
from app.repo.image import create_image_repo, create_images_repo
from app.utils.constants import (
    ALLOWED_IMAGE_TYPES,
    IMAGEKIT_FOLDER,
    MAX_IMAGE_SIZE_BYTES,
    MAX_IMAGES_PER_REQUEST,
)

logger = logging.getLogger(__name__)

_MAGIC_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
)


def _detect_image_type(content: bytes) -> str | None:
    for signature, content_type in _MAGIC_SIGNATURES:
        if content.startswith(signature):
            return content_type

    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"

    return None


async def _validate_and_read(file: UploadFile) -> tuple[str, bytes]:
    content = await file.read()

    if not content:
        raise InvalidFileError(f"File '{file.filename}' is empty")

    if len(content) > MAX_IMAGE_SIZE_BYTES:
        raise InvalidFileError(
            f"File '{file.filename}' exceeds the "
            f"{MAX_IMAGE_SIZE_BYTES // (1024 * 1024)}MB limit"
        )

    detected_type = _detect_image_type(content)
    if detected_type is None or detected_type not in ALLOWED_IMAGE_TYPES:
        raise InvalidFileError(f"File '{file.filename}' is not a supported image")

    return Path(file.filename or "file").name, content


async def delete_imagekit_files(file_ids: list[str]) -> None:
    for file_id in file_ids:
        try:
            await imagekit_client.files.delete(file_id)
        except Exception:
            logger.warning("Failed to delete ImageKit file %s", file_id, exc_info=True)


async def delete_imagekit_file(file_id: str) -> None:
    try:
        await imagekit_client.files.delete(file_id)
    except Exception:
        logger.warning("Failed to delete ImageKit file %s", file_id, exc_info=True)


async def upload_images_service(
    session: AsyncSession, files: list[UploadFile]
) -> list[Image]:
    if not files:
        raise InvalidFileError("At least one image is required")

    if len(files) > MAX_IMAGES_PER_REQUEST:
        raise InvalidFileError(
            f"At most {MAX_IMAGES_PER_REQUEST} images can be uploaded at once"
        )

    validated = [await _validate_and_read(file) for file in files]

    upload_responses: list[FileUploadResponse] = []
    try:
        for file_name, content in validated:
            response = await imagekit_client.files.upload(
                file=content,
                file_name=file_name,
                folder=IMAGEKIT_FOLDER,
            )

            if response.file_id is None:
                raise FileUploadError("ImageKit returned an invalid upload response")

            upload_responses.append(response)
    except Exception as exc:
        await delete_imagekit_files(
            [response.file_id for response in upload_responses if response.file_id]
        )
        if isinstance(exc, FileUploadError):
            raise
        raise FileUploadError("Failed to upload image") from exc

    try:
        images = await create_images_repo(session, upload_responses)
        await session.commit()
        return images
    except Exception:
        await session.rollback()
        await delete_imagekit_files(
            [response.file_id for response in upload_responses if response.file_id]
        )
        raise


async def upload_image_service(
    session: AsyncSession, file: UploadFile, *, commit: bool = True
) -> Image:
    if not file:
        raise InvalidFileError("No image found")

    file_name, content = await _validate_and_read(file)

    upload_response: FileUploadResponse | None = None
    try:
        response = await imagekit_client.files.upload(
            file=content,
            file_name=file_name,
            folder=IMAGEKIT_FOLDER,
        )

        if response.file_id is None:
            raise FileUploadError("ImageKit returned an invalid upload response")

        upload_response = response
    except Exception as exc:
        if upload_response is not None and upload_response.file_id is not None:
            await delete_imagekit_file(upload_response.file_id)
        if isinstance(exc, FileUploadError):
            raise
        raise FileUploadError("Failed to upload image") from exc

    try:
        image = await create_image_repo(session, upload_response)
        if commit:
            await session.commit()
        return image
    except Exception:
        await session.rollback()
        if upload_response.file_id is not None:
            await delete_imagekit_file(upload_response.file_id)
        raise
