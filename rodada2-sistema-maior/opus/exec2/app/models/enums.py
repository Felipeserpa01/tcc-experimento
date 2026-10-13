"""Enumerações de domínio (valores persistidos e expostos na API)."""

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "administrador"
    DOCTOR = "medico"
    NURSE = "enfermeiro"
    RECEPTIONIST = "recepcionista"
    PATIENT = "paciente"


class Sex(StrEnum):
    MALE = "masculino"
    FEMALE = "feminino"
    OTHER = "outro"


class ProfessionalType(StrEnum):
    DOCTOR = "medico"
    NURSE = "enfermeiro"


class AppointmentStatus(StrEnum):
    SCHEDULED = "agendada"
    CONFIRMED = "confirmada"
    IN_PROGRESS = "em_andamento"
    COMPLETED = "realizada"
    CANCELLED = "cancelada"
    NO_SHOW = "faltou"


ACTIVE_APPOINTMENT_STATUSES: frozenset[AppointmentStatus] = frozenset(
    {AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED, AppointmentStatus.IN_PROGRESS}
)


class WaitlistStatus(StrEnum):
    WAITING = "aguardando"
    NOTIFIED = "notificado"
    BOOKED = "agendado"
    CANCELLED = "cancelado"
    EXPIRED = "expirado"


OPEN_WAITLIST_STATUSES: frozenset[WaitlistStatus] = frozenset({WaitlistStatus.WAITING, WaitlistStatus.NOTIFIED})


class ExamStatus(StrEnum):
    REQUESTED = "solicitado"
    RESULT_AVAILABLE = "resultado_disponivel"
    CANCELLED = "cancelado"


class ChargeStatus(StrEnum):
    PENDING = "pendente"
    PAID = "pago"
    CANCELLED = "cancelado"


class PaymentMethod(StrEnum):
    CASH = "dinheiro"
    CREDIT_CARD = "cartao_credito"
    DEBIT_CARD = "cartao_debito"
    PIX = "pix"
    BANK_SLIP = "boleto"
    INSURANCE = "convenio"


class AllergySeverity(StrEnum):
    MILD = "leve"
    MODERATE = "moderada"
    SEVERE = "grave"


class NotificationChannel(StrEnum):
    SYSTEM = "sistema"
    EMAIL = "email"
