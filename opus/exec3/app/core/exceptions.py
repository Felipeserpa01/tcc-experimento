from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


class AppError(Exception):
    """Erro de domínio da aplicação, convertido em resposta HTTP pelo handler registrado."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    headers: dict[str, str] | None = None

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT


class BusinessRuleError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT


class AuthenticationError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    headers = {"WWW-Authenticate": "Bearer"}


class PermissionDeniedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN


async def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)


async def _integrity_error_handler(_: Request, __: IntegrityError) -> JSONResponse:
    # Rede de segurança para violações de restrição que escaparem das validações dos serviços
    # (ex.: duas requisições simultâneas cadastrando o mesmo ISBN).
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "A operação viola uma restrição de integridade dos dados."},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(IntegrityError, _integrity_error_handler)
