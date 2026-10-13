"""Hierarquia de erros de dominio usada por toda a aplicacao.

As rotas nunca levantam `HTTPException` diretamente: elas deixam a excecao de
dominio subir e o tratador central (`app.core.error_handlers`) converte em uma
resposta HTTP padronizada.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Erro base da aplicacao."""

    status_code: int = 500
    error_code: str = "internal_error"
    default_message: str = "Erro interno inesperado."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: Any | None = None,
        error_code: str | None = None,
        status_code: int | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details
        if error_code is not None:
            self.error_code = error_code
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.message)

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "error": {"code": self.error_code, "message": self.message}
        }
        if self.details is not None:
            payload["error"]["details"] = self.details
        return payload


class BadRequestError(AppError):
    status_code = 400
    error_code = "bad_request"
    default_message = "Requisicao invalida."


class ValidationFailedError(AppError):
    status_code = 422
    error_code = "validation_error"
    default_message = "Dados invalidos."


class BusinessRuleError(AppError):
    status_code = 422
    error_code = "business_rule_violation"
    default_message = "Operacao viola uma regra de negocio."


class AuthenticationError(AppError):
    status_code = 401
    error_code = "authentication_failed"
    default_message = "Credenciais invalidas."


class InvalidTokenError(AuthenticationError):
    error_code = "invalid_token"
    default_message = "Token invalido ou expirado."


class AccountLockedError(AppError):
    status_code = 423
    error_code = "account_locked"
    default_message = "Conta temporariamente bloqueada por tentativas de login malsucedidas."


class AccountInactiveError(AppError):
    status_code = 403
    error_code = "account_inactive"
    default_message = "Conta desativada."


class PermissionDeniedError(AppError):
    status_code = 403
    error_code = "permission_denied"
    default_message = "Voce nao tem permissao para executar esta acao."


class NotFoundError(AppError):
    status_code = 404
    error_code = "not_found"
    default_message = "Recurso nao encontrado."


class ConflictError(AppError):
    status_code = 409
    error_code = "conflict"
    default_message = "Conflito com o estado atual do recurso."


class DuplicateResourceError(ConflictError):
    error_code = "duplicate_resource"
    default_message = "Ja existe um registro com estes dados."


class ScheduleConflictError(ConflictError):
    error_code = "schedule_conflict"
    default_message = "Ja existe um agendamento para este profissional neste horario."


class PayloadTooLargeError(AppError):
    status_code = 413
    error_code = "payload_too_large"
    default_message = "Arquivo maior que o limite permitido."


class UnsupportedMediaTypeError(AppError):
    status_code = 415
    error_code = "unsupported_media_type"
    default_message = "Tipo de arquivo nao suportado."
