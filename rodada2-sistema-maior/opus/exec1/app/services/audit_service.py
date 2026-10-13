"""Servico de auditoria: registra quem fez, o que fez e quando."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.core.context import get_request_context
from app.core.pagination import PaginationParams
from app.models.audit import AuditLog
from app.models.enums import AuditStatus
from app.models.user import User
from app.repositories.audit_repository import AuditRepository


class AuditAction:
    """Catalogo de acoes auditaveis (evita strings soltas pelo codigo)."""

    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILED = "auth.login.failed"
    LOGIN_BLOCKED = "auth.login.blocked"
    ACCOUNT_LOCKED = "auth.account.locked"
    LOGOUT = "auth.logout"
    TOKEN_REFRESHED = "auth.token.refreshed"
    TOKEN_REUSE_DETECTED = "auth.token.reuse_detected"
    REGISTER = "auth.register"
    PASSWORD_CHANGED = "auth.password.changed"
    PASSWORD_RECOVERY_REQUESTED = "auth.password.recovery_requested"
    PASSWORD_RESET = "auth.password.reset"

    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DEACTIVATED = "user.deactivated"
    USER_ACTIVATED = "user.activated"
    USER_UNLOCKED = "user.unlocked"

    PATIENT_CREATED = "patient.created"
    PATIENT_UPDATED = "patient.updated"
    PATIENT_DELETED = "patient.deleted"
    PATIENT_VIEWED = "patient.viewed"

    PROFESSIONAL_CREATED = "professional.created"
    PROFESSIONAL_UPDATED = "professional.updated"
    PROFESSIONAL_DELETED = "professional.deleted"
    SCHEDULE_CREATED = "professional.schedule.created"
    SCHEDULE_UPDATED = "professional.schedule.updated"
    SCHEDULE_DELETED = "professional.schedule.deleted"

    APPOINTMENT_CREATED = "appointment.created"
    APPOINTMENT_UPDATED = "appointment.updated"
    APPOINTMENT_CONFIRMED = "appointment.confirmed"
    APPOINTMENT_CANCELLED = "appointment.cancelled"
    APPOINTMENT_RESCHEDULED = "appointment.rescheduled"
    APPOINTMENT_STARTED = "appointment.started"
    APPOINTMENT_COMPLETED = "appointment.completed"
    APPOINTMENT_NO_SHOW = "appointment.no_show"
    WAITLIST_CREATED = "waitlist.created"
    WAITLIST_CANCELLED = "waitlist.cancelled"
    WAITLIST_NOTIFIED = "waitlist.notified"

    MEDICAL_RECORD_CREATED = "medical_record.created"
    MEDICAL_RECORD_UPDATED = "medical_record.updated"
    MEDICAL_RECORD_VIEWED = "medical_record.viewed"
    PRESCRIPTION_CREATED = "prescription.created"
    PRESCRIPTION_UPDATED = "prescription.updated"
    PRESCRIPTION_DELETED = "prescription.deleted"
    EXAM_REQUESTED = "exam.requested"
    EXAM_UPDATED = "exam.updated"
    EXAM_RESULT_REGISTERED = "exam.result.registered"
    EXAM_ATTACHMENT_ADDED = "exam.attachment.added"
    EXAM_ATTACHMENT_DOWNLOADED = "exam.attachment.downloaded"

    CHARGE_CREATED = "charge.created"
    CHARGE_PAID = "charge.paid"
    CHARGE_CANCELLED = "charge.cancelled"

    REPORT_GENERATED = "report.generated"
    PERMISSION_DENIED = "security.permission_denied"


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = AuditRepository(db)

    def record(
        self,
        *,
        action: str,
        actor: User | None = None,
        resource_type: str | None = None,
        resource_id: Any | None = None,
        description: str | None = None,
        status: AuditStatus = AuditStatus.SUCCESS,
        actor_email: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> AuditLog:
        context = get_request_context()
        entry = AuditLog(
            user_id=actor.id if actor else None,
            user_email=(actor.email if actor else actor_email),
            user_role=(actor.role.value if actor else None),
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            description=description,
            status=status,
            ip_address=context.ip_address,
            user_agent=(context.user_agent or "")[:255] or None,
            request_id=context.request_id,
            http_method=context.method,
            path=(context.path or "")[:255] or None,
            extra=json.dumps(extra, ensure_ascii=False, default=str) if extra else None,
        )
        self.db.add(entry)
        self.db.flush()
        return entry

    def search(
        self,
        pagination: PaginationParams,
        *,
        user_id: int | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        status: AuditStatus | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[list[AuditLog], int]:
        return self.repository.search(
            pagination,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            start_date=start_date,
            end_date=end_date,
        )
