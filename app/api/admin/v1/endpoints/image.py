from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.v1.endpoints.auth import get_current_user_controller
from app.core.api_response import ApiResponse, ErrorResponse
from app.db.session import get_db
from app.schemas.image import ImageResponse
from app.services.image import upload_images_service
from app.utils.constants import HTTP_RESPONSE_MESSAGES, HTTP_STATUS_CODES

router = APIRouter(tags=["Image"], dependencies=[Depends(get_current_user_controller)])


@router.post(
    "/",
    status_code=HTTP_STATUS_CODES.CREATED.value,
    response_model=ApiResponse[list[ImageResponse]],
    summary="Upload images",
    description=(
        "Uploads one or more images to the ImageKit media library and registers "
        "them in the image pool. Returns the created image records so they can be "
        "linked to products."
    ),
    responses={
        HTTP_STATUS_CODES.BAD_REQUEST.value: {
            "model": ErrorResponse,
            "description": "No files, too many files, or an unsupported/oversized file.",
        },
    },
)
async def upload_images_controller(
    files: list[UploadFile] = File(...),
    session: AsyncSession = Depends(get_db),
):
    images = await upload_images_service(session, files)

    return ApiResponse[list[ImageResponse]](
        message=HTTP_RESPONSE_MESSAGES.CREATED.value,
        data=[ImageResponse.model_validate(image) for image in images],
    )
