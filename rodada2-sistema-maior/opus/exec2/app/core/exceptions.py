"""Exceções de domínio.

Os serviços lançam estas exceções; o tratamento centralizado (``error_handlers``)
converte cada uma no código HTTP adequado com um corpo de resposta padronizado.
"""

from typing import Any


class AppError(Exception):
    status_code: int = 400
    code: str = "erro"

    def __init__(self, message: str, *, details: Any = None, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details
        if code is not None:
            self.code = code


class InvalidInputError(AppError):
    status_code = 422
    code = "dados_invalidos"


class BusinessRuleError(AppError):
    status_code = 422
    code = "regra_de_negocio"


class AuthenticationError(AppError):
    status_code = 401
    code = "nao_autenticado"


class PermissionDeniedError(AppError):
    status_code = 403
    code = "acesso_negado"


class NotFoundError(AppError):
    status_code = 404
    code = "nao_encontrado"


class ConflictError(AppError):
    status_code = 409
    code = "conflito"


class PayloadTooLargeError(AppError):
    status_code = 413
    code = "arquivo_muito_grande"


class UnsupportedMediaTypeError(AppError):
    status_code = 415
    code = "tipo_de_arquivo_nao_suportado"


class AccountLockedError(AppError):
    status_code = 423
    code = "conta_bloqueada"
