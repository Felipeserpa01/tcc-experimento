from fastapi import status


class AppError(Exception):
    """Base application exception mapped to an HTTP status code."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_message = "Erro na requisição."

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
    default_message = "Credenciais inválidas."


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    default_message = "Você não tem permissão para executar esta ação."


class AccountLockedError(AppError):
    status_code = status.HTTP_423_LOCKED
    default_message = "Conta bloqueada temporariamente devido a múltiplas tentativas de login inválidas."
