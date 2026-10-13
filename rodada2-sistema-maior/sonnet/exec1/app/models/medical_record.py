from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MedicalRecord(Base):
    """Prontuário: clinical record of a completed consultation."""

    __tablename__ = "medical_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id"), unique=True, nullable=False, index=True
    )
    complaint: Mapped[str] = mapped_column(Text, nullable=False)
    diagnosis: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    appointment: Mapped["Appointment"] = relationship(back_populates="medical_record")
    prescriptions: Mapped[list["Prescription"]] = relationship(
        back_populates="medical_record", cascade="all, delete-orphan"
    )
    exams: Mapped[list["Exam"]] = relationship(
        back_populates="medical_record", cascade="all, delete-orphan"
    )


class Prescription(Base):
    __tablename__ = "prescriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    medical_record_id: Mapped[int] = mapped_column(
        ForeignKey("medical_records.id"), nullable=False, index=True
    )
    medication_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dosage: Mapped[str] = mapped_column(String(100), nullable=False)
    frequency: Mapped[str] = mapped_column(String(100), nullable=False)
    duration: Mapped[str] = mapped_column(String(100), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    medical_record: Mapped["MedicalRecord"] = relationship(back_populates="prescriptions")


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    medical_record_id: Mapped[int] = mapped_column(
        ForeignKey("medical_records.id"), nullable=False, index=True
    )
    exam_name: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_attached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    medical_record: Mapped["MedicalRecord"] = relationship(back_populates="exams")
