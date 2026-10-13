class AppException(Exception):
    """Base exception for the application."""
    def __init__(self, message: str, code: str = None, status_code: int = 500):
        self.message = message
        self.code = code or self.__class__.__name__
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found", code: str = "NOT_FOUND"):
        super().__init__(message, code, 404)


class ConflictError(AppException):
    def __init__(self, message: str = "Conflict", code: str = "CONFLICT"):
        super().__init__(message, code, 409)


class ForbiddenError(AppException):
    def __init__(self, message: str = "Access denied", code: str = "FORBIDDEN"):
        super().__init__(message, code, 403)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Unauthorized", code: str = "UNAUTHORIZED"):
        super().__init__(message, code, 401)


class ValidationError(AppException):
    def __init__(self, message: str = "Validation failed", code: str = "VALIDATION_ERROR"):
        super().__init__(message, code, 422)


class AccountLockedError(AppException):
    def __init__(self, message: str = "Account is temporarily locked", code: str = "ACCOUNT_LOCKED"):
        super().__init__(message, code, 423)


class InvalidTokenError(AppException):
    def __init__(self, message: str = "Invalid token", code: str = "INVALID_TOKEN"):
        super().__init__(message, code, 401)
