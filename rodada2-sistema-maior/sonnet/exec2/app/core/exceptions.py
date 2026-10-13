"""Domain-level exceptions and the centralized FastAPI exception handlers."""
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base class for all domain/application errors."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_message = "Erro na aplicação."

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    default_message = "Recurso não encontrado."


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    default_message = "Conflito com o estado atual do recurso."


class ValidationAppError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_message = "Dados inválidos."


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_message = "Credenciais inválidas ou ausentes."


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    default_message = "Você não tem permissão para executar esta ação."


class AccountLockedError(AppError):
    status_code = status.HTTP_423_LOCKED
    default_message = "Conta temporariamente bloqueada devido a tentativas de login malsucedidas."


class BusinessRuleError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_message = "Regra de negócio violada."


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "error_type": exc.__class__.__name__},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        errors = [
            {
                "field": ".".join(str(loc) for loc in err["loc"] if loc != "body"),
                "message": err["msg"],
                "type": err["type"],
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Erro de validação nos dados enviados.", "errors": errors},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Erro interno do servidor."},
        )
