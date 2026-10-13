from app.utils.constants import HTTP_RESPONSE_MESSAGES, HTTP_STATUS_CODES


class AppError(Exception):
    """Base exception for expected application errors."""

    def __init__(
        self,
        message: str,
        code: str = HTTP_RESPONSE_MESSAGES.INTERNAL_SERVER_ERROR.value,
        status: int = HTTP_STATUS_CODES.INTERNAL_SERVER_ERROR.value,
    ):
        self.message = message
        self.code = code
        self.status = status
        super().__init__(message)


class ResourceNotFoundError(AppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(
            message,
            HTTP_RESPONSE_MESSAGES.RESOURCE_NOT_FOUND.value,
            HTTP_STATUS_CODES.RESOURCE_NOT_FOUND.value,
        )


class ConflictError(AppError):
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(
            message,
            HTTP_RESPONSE_MESSAGES.CONFLICT.value,
            HTTP_STATUS_CODES.CONFLICT.value,
        )


class UnauthorizedAccessError(AppError):
    def __init__(self, message: str = "Unauthorized access"):
        super().__init__(
            message,
            HTTP_RESPONSE_MESSAGES.UNAUTHORIZED.value,
            HTTP_STATUS_CODES.UNAUTHORIZED.value,
        )


class BadRequestError(AppError):
    def __init__(self, message: str = "Bad request"):
        super().__init__(
            message,
            HTTP_RESPONSE_MESSAGES.BAD_REQUEST.value,
            HTTP_STATUS_CODES.BAD_REQUEST.value,
        )


class CannotDeleteError(AppError):
    def __init__(
        self,
        message: str = "Resource cannot be deleted",
        code: str = HTTP_RESPONSE_MESSAGES.CANNOT_DELETE.value,
        status: int = HTTP_STATUS_CODES.BAD_REQUEST.value,
    ):
        super().__init__(message, code, status)


class InvalidFileError(AppError):
    def __init__(
        self,
        message: str,
        code: str = HTTP_RESPONSE_MESSAGES.VALIDATION_ERROR.value,
        status: int = HTTP_STATUS_CODES.BAD_REQUEST.value,
    ):
        super().__init__(message, code, status)


class FileUploadError(AppError):
    def __init__(
        self,
        message: str,
        code: str = HTTP_RESPONSE_MESSAGES.FILE_UPLOAD_ERROR.value,
        status: int = HTTP_STATUS_CODES.INTERNAL_SERVER_ERROR.value,
    ):
        super().__init__(message, code, status)
