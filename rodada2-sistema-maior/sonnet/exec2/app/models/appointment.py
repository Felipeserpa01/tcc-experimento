"""Appointment and waitlist models."""
from datetime import date, datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.enums import AppointmentStatus, WaitlistStatus
from app.database import Base


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    professional_id: Mapped[int] = mapped_column(ForeignKey("professionals.id"), nullable=False)

    data_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    duracao_minutos: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus), default=AppointmentStatus.AGENDADA, nullable=False, index=True
    )
    motivo_cancelamento: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    patient = relationship("Patient", back_populates="appointments")
    professional = relationship("Professional", back_populates="appointments")
    medical_record = relationship(
        "MedicalRecord", back_populates="appointment", uselist=False, cascade="all, delete-orphan"
    )
    prescriptions = relationship(
        "Prescription", back_populates="appointment", cascade="all, delete-orphan"
    )
    exams = relationship("Exam", back_populates="appointment", cascade="all, delete-orphan")
    billings = relationship("Billing", back_populates="appointment")


class WaitlistEntry(Base):
    __tablename__ = "waitlist_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    professional_id: Mapped[int] = mapped_column(ForeignKey("professionals.id"), nullable=False)
    data_desejada: Mapped[date] = mapped_column(nullable=False)
    status: Mapped[WaitlistStatus] = mapped_column(
        Enum(WaitlistStatus), default=WaitlistStatus.AGUARDANDO, nullable=False, index=True
    )
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("Patient", back_populates="waitlist_entries")
    professional = relationship("Professional", back_populates="waitlist_entries")
