"""Modelos ORM. Importar este pacote registra todas as tabelas no metadata."""

from app.models.appointment import Appointment, WaitlistEntry
from app.models.audit import AuditLog
from app.models.billing import Charge
from app.models.clinical import ExamRequest, MedicalRecord, Prescription
from app.models.notification import Notification
from app.models.patient import HealthInsurance, Patient
from app.models.professional import Availability, Professional
from app.models.user import PasswordResetToken, RefreshToken, User

__all__ = [
    "Appointment",
    "AuditLog",
    "Availability",
    "Charge",
    "ExamRequest",
    "HealthInsurance",
    "MedicalRecord",
    "Notification",
    "PasswordResetToken",
    "Patient",
    "Prescription",
    "Professional",
    "RefreshToken",
    "User",
    "WaitlistEntry",
]
