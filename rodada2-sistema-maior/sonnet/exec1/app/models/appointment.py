from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import AppointmentStatus


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("professionals.id"), nullable=False, index=True)

    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus), default=AppointmentStatus.SCHEDULED, nullable=False, index=True
    )
    cancellation_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    patient: Mapped["Patient"] = relationship(back_populates="appointments")
    doctor: Mapped["Professional"] = relationship(back_populates="appointments")
    medical_record: Mapped["MedicalRecord"] = relationship(
        back_populates="appointment", uselist=False, cascade="all, delete-orphan"
    )
    billings: Mapped[list["Billing"]] = relationship(
        back_populates="appointment", cascade="all, delete-orphan"
    )


class WaitListEntry(Base):
    __tablename__ = "waitlist_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("professionals.id"), nullable=False, index=True)
    desired_date: Mapped[date] = mapped_column(Date, nullable=False)
    notified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    patient: Mapped["Patient"] = relationship()
    doctor: Mapped["Professional"] = relationship()
