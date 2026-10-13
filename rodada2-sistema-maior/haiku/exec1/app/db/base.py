from sqlalchemy.orm import declarative_base

DeclarativeBase = declarative_base()

# Import all models here for Alembic metadata discovery
from app.models.user import User
from app.models.patient import Patient
from app.models.professional import Professional
from app.models.availability import AvailabilitySlot
from app.models.appointment import Appointment
from app.models.waitlist import WaitlistEntry
from app.models.medical_record import MedicalRecord
from app.models.prescription import Prescription
from app.models.exam import Exam
from app.models.billing import Charge, Payment
from app.models.audit_log import AuditLog
from app.models.refresh_token import RefreshToken
from app.models.password_reset import PasswordResetToken

__all__ = [
    "DeclarativeBase",
    "User",
    "Patient",
    "Professional",
    "AvailabilitySlot",
    "Appointment",
    "WaitlistEntry",
    "MedicalRecord",
    "Prescription",
    "Exam",
    "Charge",
    "Payment",
    "AuditLog",
    "RefreshToken",
    "PasswordResetToken",
]
