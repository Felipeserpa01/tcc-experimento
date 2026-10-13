"""Prontuario, prescricoes, exames e anexos de resultado."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.datetime_utils import now
from app.db.base import Base, TimestampMixin
from app.models.enums import ExamStatus, enum_column

if TYPE_CHECKING:  # pragma: no cover
    from app.models.appointment import Appointment
    from app.models.billing import Charge
    from app.models.patient import Patient
    from app.models.professional import Professional
    from app.models.user import User


class MedicalRecord(Base, TimestampMixin):
    """Prontuario de uma consulta realizada (1:1 com a consulta)."""

    __tablename__ = "medical_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    professional_id: Mapped[int] = mapped_column(
        ForeignKey("professionals.id", ondelete="CASCADE"), nullable=False, index=True
    )

    chief_complaint: Mapped[str] = mapped_column(Text, nullable=False)
    history: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    physical_exam: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    diagnosis: Mapped[str] = mapped_column(Text, nullable=False)
    icd10_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    treatment_plan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    observations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Sinais vitais
    blood_pressure: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    heart_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    temperature_celsius: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 1), nullable=True)
    weight_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    height_cm: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 1), nullable=True)

    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False, index=True)

    appointment: Mapped["Appointment"] = relationship("Appointment", back_populates="medical_record")
    patient: Mapped["Patient"] = relationship("Patient", back_populates="medical_records")
    professional: Mapped["Professional"] = relationship("Professional")
    prescriptions: Mapped[list["Prescription"]] = relationship(
        "Prescription", back_populates="medical_record"
    )
    exam_requests: Mapped[list["ExamRequest"]] = relationship(
        "ExamRequest", back_populates="medical_record"
    )


class Prescription(Base, TimestampMixin):
    """Medicamento prescrito em uma consulta."""

    __tablename__ = "prescriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    medical_record_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("medical_records.id", ondelete="SET NULL"), nullable=True, index=True
    )
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    professional_id: Mapped[int] = mapped_column(
        ForeignKey("professionals.id", ondelete="CASCADE"), nullable=False, index=True
    )

    medication_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    dosage: Mapped[str] = mapped_column(String(80), nullable=False)
    frequency: Mapped[str] = mapped_column(String(80), nullable=False)
    duration: Mapped[str] = mapped_column(String(80), nullable=False)
    route: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prescribed_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False, index=True)

    appointment: Mapped["Appointment"] = relationship("Appointment", back_populates="prescriptions")
    medical_record: Mapped[Optional["MedicalRecord"]] = relationship(
        "MedicalRecord", back_populates="prescriptions"
    )
    patient: Mapped["Patient"] = relationship("Patient", back_populates="prescriptions")
    professional: Mapped["Professional"] = relationship("Professional")


class ExamRequest(Base, TimestampMixin):
    """Exame solicitado durante a consulta, com resultado e anexos."""

    __tablename__ = "exam_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    medical_record_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("medical_records.id", ondelete="SET NULL"), nullable=True, index=True
    )
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    professional_id: Mapped[int] = mapped_column(
        ForeignKey("professionals.id", ondelete="CASCADE"), nullable=False, index=True
    )

    exam_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    exam_type: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    clinical_indication: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ExamStatus] = mapped_column(
        enum_column(ExamStatus), default=ExamStatus.REQUESTED, nullable=False, index=True
    )
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)

    requested_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False, index=True)
    result_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_registered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    result_registered_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    cancellation_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    appointment: Mapped["Appointment"] = relationship("Appointment", back_populates="exam_requests")
    medical_record: Mapped[Optional["MedicalRecord"]] = relationship(
        "MedicalRecord", back_populates="exam_requests"
    )
    patient: Mapped["Patient"] = relationship("Patient", back_populates="exam_requests")
    professional: Mapped["Professional"] = relationship("Professional")
    attachments: Mapped[list["ExamAttachment"]] = relationship(
        "ExamAttachment", back_populates="exam", cascade="all, delete-orphan"
    )
    charges: Mapped[list["Charge"]] = relationship("Charge", back_populates="exam")


class ExamAttachment(Base):
    """Arquivo de resultado anexado a um exame."""

    __tablename__ = "exam_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(
        ForeignKey("exam_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    uploaded_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)

    exam: Mapped["ExamRequest"] = relationship("ExamRequest", back_populates="attachments")
    uploaded_by: Mapped[Optional["User"]] = relationship("User")
