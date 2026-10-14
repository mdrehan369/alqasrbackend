from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer

from app.core.api_response import ApiResponse
from app.schemas.auth import AccessTokenData, SigninRequest, SigninResponse
from app.services.auth import get_current_user_service, signin_service
from app.utils.constants import HTTP_RESPONSE_MESSAGES, HTTP_STATUS_CODES

router = APIRouter(tags=["Auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="signin", auto_error=False)


@router.post(
    "/",
    status_code=HTTP_STATUS_CODES.SUCCESS.value,
    response_model=ApiResponse[SigninResponse],
)
async def signin_controller(payload: SigninRequest):
    response = await signin_service(payload)
    return ApiResponse[SigninResponse](
        message=HTTP_RESPONSE_MESSAGES.SUCCESS.value,
        data=SigninResponse.model_validate(response),
    )


@router.get(
    "/me",
    status_code=HTTP_STATUS_CODES.SUCCESS.value,
    response_model=ApiResponse[AccessTokenData],
)
async def get_current_user_controller(
    access_token: Annotated[str, Depends(oauth2_scheme)],
):
    data = await get_current_user_service(access_token)
    return ApiResponse[AccessTokenData](
        message=HTTP_RESPONSE_MESSAGES.SUCCESS.value,
        data=AccessTokenData.model_validate(data),
    )
