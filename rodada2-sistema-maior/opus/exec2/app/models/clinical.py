"""Prontuário, prescrições e exames."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.appointment import Appointment
from app.models.base import TimestampMixin, current_time
from app.models.enums import ExamStatus
from app.models.professional import Professional
from app.models.types import enum_type


class MedicalRecord(TimestampMixin, Base):
    __tablename__ = "medical_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id", ondelete="RESTRICT"), unique=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="RESTRICT"), index=True)
    professional_id: Mapped[int] = mapped_column(ForeignKey("professionals.id", ondelete="RESTRICT"))
    chief_complaint: Mapped[str] = mapped_column(Text)
    diagnosis: Mapped[str] = mapped_column(Text)
    icd10_code: Mapped[str | None] = mapped_column(String(7))
    notes: Mapped[str | None] = mapped_column(Text)

    appointment: Mapped[Appointment] = relationship(back_populates="medical_record")
    professional: Mapped[Professional] = relationship(lazy="joined")

    @property
    def professional_name(self) -> str:
        return self.professional.full_name


class Prescription(Base):
    __tablename__ = "prescriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id", ondelete="RESTRICT"), index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="RESTRICT"), index=True)
    professional_id: Mapped[int] = mapped_column(ForeignKey("professionals.id", ondelete="RESTRICT"))
    medication_name: Mapped[str] = mapped_column(String(150))
    dosage: Mapped[str] = mapped_column(String(100))
    frequency: Mapped[str] = mapped_column(String(100))
    duration: Mapped[str] = mapped_column(String(100))
    instructions: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=current_time)


class ExamRequest(TimestampMixin, Base):
    __tablename__ = "exam_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id", ondelete="RESTRICT"), index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="RESTRICT"), index=True)
    professional_id: Mapped[int] = mapped_column(ForeignKey("professionals.id", ondelete="RESTRICT"))
    exam_name: Mapped[str] = mapped_column(String(150))
    clinical_indication: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[ExamStatus] = mapped_column(enum_type(ExamStatus), default=ExamStatus.REQUESTED, index=True)
    result_text: Mapped[str | None] = mapped_column(Text)
    result_file_path: Mapped[str | None] = mapped_column(String(255))
    result_file_name: Mapped[str | None] = mapped_column(String(255))
    result_content_type: Mapped[str | None] = mapped_column(String(100))
    result_registered_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)

    appointment: Mapped[Appointment] = relationship(back_populates="exams")

    @property
    def requested_at(self) -> datetime:
        return self.created_at

    @property
    def has_result_file(self) -> bool:
        return self.result_file_path is not None
