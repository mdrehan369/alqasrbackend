import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError
from app.utils.constants import HTTP_RESPONSE_MESSAGES, HTTP_STATUS_CODES

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(AppError)
    async def handle_app_error(
        request: Request,
        exc: AppError,
    ):
        return JSONResponse(
            status_code=exc.status,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                },
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request,
        exc: Exception,
    ):
        logger.exception(
            "Unhandled exception while processing %s %s",
            request.method,
            request.url.path,
        )

        return JSONResponse(
            status_code=HTTP_STATUS_CODES.INTERNAL_SERVER_ERROR.value,
            content={
                "success": False,
                "error": {
                    "code": HTTP_RESPONSE_MESSAGES.INTERNAL_SERVER_ERROR.value,
                    "message": "An unexpected error occurred",
                },
            },
        )
