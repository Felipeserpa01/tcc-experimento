"""Enumeracoes de dominio compartilhadas entre modelos, schemas e servicos."""

from __future__ import annotations

from enum import Enum

from sqlalchemy import Enum as SAEnum


class DomainEnum(str, Enum):
    """Enum serializavel como string (compativel com Pydantic e SQLAlchemy)."""

    def __str__(self) -> str:  # pragma: no cover - acucar sintatico
        return str(self.value)


def enum_column(enum_cls: type[DomainEnum], length: int = 32) -> SAEnum:
    """Coluna de enum portatil (armazenada como VARCHAR com CHECK)."""
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=length,
        values_callable=lambda cls: [member.value for member in cls],
        validate_strings=True,
    )


class UserRole(DomainEnum):
    ADMIN = "admin"
    DOCTOR = "doctor"
    NURSE = "nurse"
    RECEPTIONIST = "receptionist"
    PATIENT = "patient"


#: Perfis internos da clinica (tudo menos o paciente).
STAFF_ROLES = frozenset(
    {UserRole.ADMIN, UserRole.DOCTOR, UserRole.NURSE, UserRole.RECEPTIONIST}
)
#: Perfis assistenciais.
CLINICAL_ROLES = frozenset({UserRole.DOCTOR, UserRole.NURSE})
#: Perfis com visao administrativa da agenda.
FRONT_DESK_ROLES = frozenset({UserRole.ADMIN, UserRole.RECEPTIONIST})


class Gender(DomainEnum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    NOT_INFORMED = "not_informed"


class ProfessionalType(DomainEnum):
    DOCTOR = "doctor"
    NURSE = "nurse"


class CouncilType(DomainEnum):
    CRM = "CRM"
    COREN = "COREN"


class AppointmentStatus(DomainEnum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


#: Status que ocupam a agenda do profissional.
ACTIVE_APPOINTMENT_STATUSES = frozenset(
    {
        AppointmentStatus.SCHEDULED,
        AppointmentStatus.CONFIRMED,
        AppointmentStatus.IN_PROGRESS,
    }
)
#: Status terminais (nao admitem novas transicoes).
FINAL_APPOINTMENT_STATUSES = frozenset(
    {
        AppointmentStatus.COMPLETED,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.NO_SHOW,
    }
)


class WaitlistStatus(DomainEnum):
    WAITING = "waiting"
    NOTIFIED = "notified"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ExamStatus(DomainEnum):
    REQUESTED = "requested"
    SCHEDULED = "scheduled"
    COLLECTED = "collected"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ChargeStatus(DomainEnum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"


class ChargeType(DomainEnum):
    APPOINTMENT = "appointment"
    EXAM = "exam"
    OTHER = "other"


class PaymentMethod(DomainEnum):
    CASH = "cash"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PIX = "pix"
    BANK_TRANSFER = "bank_transfer"
    HEALTH_INSURANCE = "health_insurance"


class NotificationType(DomainEnum):
    WAITLIST_SLOT_AVAILABLE = "waitlist_slot_available"
    APPOINTMENT_CONFIRMED = "appointment_confirmed"
    APPOINTMENT_CANCELLED = "appointment_cancelled"
    APPOINTMENT_RESCHEDULED = "appointment_rescheduled"
    EXAM_RESULT_AVAILABLE = "exam_result_available"
    PASSWORD_RECOVERY = "password_recovery"
    GENERIC = "generic"


class AuditStatus(DomainEnum):
    SUCCESS = "success"
    FAILURE = "failure"
