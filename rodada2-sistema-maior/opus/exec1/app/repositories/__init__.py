"""Camada de acesso a dados."""

from app.repositories.appointment_repository import AppointmentRepository, WaitlistRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.base import BaseRepository
from app.repositories.billing_repository import ChargeRepository
from app.repositories.medical_record_repository import (
    ExamAttachmentRepository,
    ExamRepository,
    MedicalRecordRepository,
    PrescriptionRepository,
)
from app.repositories.patient_repository import HealthInsuranceRepository, PatientRepository
from app.repositories.professional_repository import ProfessionalRepository, ScheduleRepository
from app.repositories.user_repository import (
    NotificationRepository,
    PasswordResetTokenRepository,
    RefreshTokenRepository,
    UserRepository,
)

__all__ = [
    "AppointmentRepository",
    "AuditRepository",
    "BaseRepository",
    "ChargeRepository",
    "ExamAttachmentRepository",
    "ExamRepository",
    "HealthInsuranceRepository",
    "MedicalRecordRepository",
    "NotificationRepository",
    "PasswordResetTokenRepository",
    "PatientRepository",
    "PrescriptionRepository",
    "ProfessionalRepository",
    "RefreshTokenRepository",
    "ScheduleRepository",
    "UserRepository",
    "WaitlistRepository",
]
