"""Log de auditoria de ações sensíveis."""

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.core.context import client_ip_var, request_id_var
from app.core.exceptions import InvalidInputError
from app.core.pagination import PageParams, PageResult, SortParams
from app.models.audit import AuditLog
from app.models.user import User
from app.repositories.audit_repository import AuditLogRepository


class AuditAction:
    LOGIN_SUCCESS = "auth.login.sucesso"
    LOGIN_FAILED = "auth.login.falha"
    LOGIN_BLOCKED = "auth.login.bloqueado"
    ACCOUNT_LOCKED = "auth.conta.bloqueada"
    LOGOUT = "auth.logout"
    REFRESH_REUSE = "auth.refresh_token.reutilizado"
    PASSWORD_CHANGED = "auth.senha.alterada"
    PASSWORD_RESET_REQUESTED = "auth.senha.recuperacao_solicitada"
    PASSWORD_RESET = "auth.senha.redefinida"
    REGISTER = "auth.registro"

    USER_CREATED = "usuario.criado"
    USER_UPDATED = "usuario.atualizado"
    USER_UNLOCKED = "usuario.desbloqueado"

    INSURANCE_CREATED = "convenio.criado"
    INSURANCE_UPDATED = "convenio.atualizado"

    PATIENT_CREATED = "paciente.criado"
    PATIENT_UPDATED = "paciente.atualizado"
    PATIENT_DEACTIVATED = "paciente.desativado"

    PROFESSIONAL_CREATED = "profissional.criado"
    PROFESSIONAL_UPDATED = "profissional.atualizado"
    PROFESSIONAL_DEACTIVATED = "profissional.desativado"
    AVAILABILITY_CREATED = "agenda.disponibilidade_criada"
    AVAILABILITY_DELETED = "agenda.disponibilidade_removida"

    APPOINTMENT_CREATED = "consulta.agendada"
    APPOINTMENT_CONFIRMED = "consulta.confirmada"
    APPOINTMENT_CANCELLED = "consulta.cancelada"
    APPOINTMENT_RESCHEDULED = "consulta.remarcada"
    APPOINTMENT_STARTED = "consulta.iniciada"
    APPOINTMENT_COMPLETED = "consulta.realizada"
    APPOINTMENT_NO_SHOW = "consulta.falta"

    MEDICAL_RECORD_CREATED = "prontuario.criado"
    MEDICAL_RECORD_UPDATED = "prontuario.atualizado"
    MEDICAL_RECORD_VIEWED = "prontuario.visualizado"
    CLINICAL_HISTORY_VIEWED = "historico_clinico.visualizado"
    PRESCRIPTION_CREATED = "prescricao.criada"
    EXAM_REQUESTED = "exame.solicitado"
    EXAM_RESULT_ATTACHED = "exame.resultado_anexado"
    EXAM_RESULT_DOWNLOADED = "exame.resultado_baixado"
    EXAM_CANCELLED = "exame.cancelado"

    CHARGE_CREATED = "cobranca.criada"
    CHARGE_PAID = "cobranca.paga"
    CHARGE_CANCELLED = "cobranca.cancelada"


class AuditService:
    def __init__(self, db: Session) -> None:
        self.repo = AuditLogRepository(db)

    def log(
        self,
        action: str,
        *,
        actor: User | None = None,
        entity_type: str | None = None,
        entity_id: int | str | None = None,
        details: dict[str, Any] | None = None,
        actor_email: str | None = None,
    ) -> AuditLog:
        """Registra a ação na transação corrente (persistida no commit do serviço chamador).

        Nunca inclua senhas, tokens ou dados clínicos em ``details``.
        """
        entry = AuditLog(
            user_id=actor.id if actor else None,
            user_email=actor.email if actor else actor_email,
            user_role=actor.role.value if actor else None,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=details,
            ip_address=client_ip_var.get(),
            request_id=request_id_var.get(),
        )
        return self.repo.add(entry)

    def search(
        self,
        page: PageParams,
        sort: SortParams,
        *,
        user_id: int | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> PageResult[AuditLog]:
        if date_from and date_to and date_from > date_to:
            raise InvalidInputError("'date_from' deve ser anterior ou igual a 'date_to'.")
        return self.repo.search(
            page,
            sort,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            date_from=date_from,
            date_to=date_to,
        )
