"""Exceções de domínio, convertidas em respostas HTTP pelos handlers da API."""


class AppError(Exception):
    status_code: int = 400
    code: str = "bad_request"

    def __init__(self, detail: str, *, code: str | None = None, headers: dict[str, str] | None = None):
        super().__init__(detail)
        self.detail = detail
        if code is not None:
            self.code = code
        self.headers = headers


class InvalidOperationError(AppError):
    status_code = 400
    code = "invalid_operation"


class AuthenticationError(AppError):
    status_code = 401
    code = "not_authenticated"

    def __init__(self, detail: str = "Não autenticado", *, code: str | None = None):
        super().__init__(detail, code=code, headers={"WWW-Authenticate": "Bearer"})


class PermissionDeniedError(AppError):
    status_code = 403
    code = "permission_denied"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
