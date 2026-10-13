"""Registro central dos modelos (import obrigatorio para o metadata do ORM)."""

from app.models.appointment import (
    ALLOWED_STATUS_TRANSITIONS,
    Appointment,
    WaitlistEntry,
)
from app.models.audit import AuditLog
from app.models.billing import Charge
from app.models.enums import (
    ACTIVE_APPOINTMENT_STATUSES,
    CLINICAL_ROLES,
    FINAL_APPOINTMENT_STATUSES,
    FRONT_DESK_ROLES,
    STAFF_ROLES,
    AppointmentStatus,
    AuditStatus,
    ChargeStatus,
    ChargeType,
    CouncilType,
    ExamStatus,
    Gender,
    NotificationType,
    PaymentMethod,
    ProfessionalType,
    UserRole,
    WaitlistStatus,
)
from app.models.medical_record import (
    ExamAttachment,
    ExamRequest,
    MedicalRecord,
    Prescription,
)
from app.models.notification import Notification
from app.models.patient import HealthInsurance, Patient
from app.models.professional import Professional, ProfessionalSchedule
from app.models.user import PasswordResetToken, RefreshToken, User

__all__ = [
    "ACTIVE_APPOINTMENT_STATUSES",
    "ALLOWED_STATUS_TRANSITIONS",
    "CLINICAL_ROLES",
    "FINAL_APPOINTMENT_STATUSES",
    "FRONT_DESK_ROLES",
    "STAFF_ROLES",
    "Appointment",
    "AppointmentStatus",
    "AuditLog",
    "AuditStatus",
    "Charge",
    "ChargeStatus",
    "ChargeType",
    "CouncilType",
    "ExamAttachment",
    "ExamRequest",
    "ExamStatus",
    "Gender",
    "HealthInsurance",
    "MedicalRecord",
    "Notification",
    "NotificationType",
    "PasswordResetToken",
    "Patient",
    "PaymentMethod",
    "Prescription",
    "Professional",
    "ProfessionalSchedule",
    "ProfessionalType",
    "RefreshToken",
    "User",
    "UserRole",
    "WaitlistEntry",
    "WaitlistStatus",
]
