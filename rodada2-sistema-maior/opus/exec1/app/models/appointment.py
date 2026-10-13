"""Consultas e lista de espera."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import (
    ACTIVE_APPOINTMENT_STATUSES,
    FINAL_APPOINTMENT_STATUSES,
    AppointmentStatus,
    WaitlistStatus,
    enum_column,
)

if TYPE_CHECKING:  # pragma: no cover
    from app.models.billing import Charge
    from app.models.medical_record import ExamRequest, MedicalRecord, Prescription
    from app.models.patient import Patient
    from app.models.professional import Professional
    from app.models.user import User

#: Transicoes permitidas no ciclo de vida da consulta.
ALLOWED_STATUS_TRANSITIONS: dict[AppointmentStatus, set[AppointmentStatus]] = {
    AppointmentStatus.SCHEDULED: {
        AppointmentStatus.CONFIRMED,
        AppointmentStatus.IN_PROGRESS,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.NO_SHOW,
    },
    AppointmentStatus.CONFIRMED: {
        AppointmentStatus.IN_PROGRESS,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.NO_SHOW,
    },
    AppointmentStatus.IN_PROGRESS: {
        AppointmentStatus.COMPLETED,
        AppointmentStatus.CANCELLED,
    },
    AppointmentStatus.COMPLETED: set(),
    AppointmentStatus.CANCELLED: set(),
    AppointmentStatus.NO_SHOW: set(),
}


class Appointment(Base, TimestampMixin):
    """Consulta agendada entre um paciente e um profissional."""

    __tablename__ = "appointments"
    __table_args__ = (
        Index("ix_appointments_professional_window", "professional_id", "scheduled_start", "scheduled_end"),
        Index("ix_appointments_patient_window", "patient_id", "scheduled_start"),
        CheckConstraint("scheduled_end > scheduled_start", name="ck_appointment_window"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    professional_id: Mapped[int] = mapped_column(
        ForeignKey("professionals.id", ondelete="CASCADE"), nullable=False, index=True
    )

    scheduled_start: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    scheduled_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[AppointmentStatus] = mapped_column(
        enum_column(AppointmentStatus),
        default=AppointmentStatus.SCHEDULED,
        nullable=False,
        index=True,
    )
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cancelled_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    rescheduled_from_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True
    )

    patient: Mapped["Patient"] = relationship("Patient", back_populates="appointments")
    professional: Mapped["Professional"] = relationship("Professional", back_populates="appointments")
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])
    cancelled_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[cancelled_by_id])
    medical_record: Mapped[Optional["MedicalRecord"]] = relationship(
        "MedicalRecord", back_populates="appointment", uselist=False, cascade="all, delete-orphan"
    )
    prescriptions: Mapped[list["Prescription"]] = relationship(
        "Prescription", back_populates="appointment", cascade="all, delete-orphan"
    )
    exam_requests: Mapped[list["ExamRequest"]] = relationship(
        "ExamRequest", back_populates="appointment", cascade="all, delete-orphan"
    )
    charges: Mapped[list["Charge"]] = relationship("Charge", back_populates="appointment")

    @property
    def occupies_agenda(self) -> bool:
        return self.status in ACTIVE_APPOINTMENT_STATUSES

    @property
    def is_final(self) -> bool:
        return self.status in FINAL_APPOINTMENT_STATUSES

    def can_transition_to(self, target: AppointmentStatus) -> bool:
        return target in ALLOWED_STATUS_TRANSITIONS.get(self.status, set())


class WaitlistEntry(Base, TimestampMixin):
    """Paciente aguardando a liberacao de um horario com determinado profissional."""

    __tablename__ = "waitlist_entries"
    __table_args__ = (
        Index("ix_waitlist_lookup", "professional_id", "desired_date", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    professional_id: Mapped[int] = mapped_column(
        ForeignKey("professionals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    desired_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    preferred_start_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    preferred_end_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    status: Mapped[WaitlistStatus] = mapped_column(
        enum_column(WaitlistStatus), default=WaitlistStatus.WAITING, nullable=False, index=True
    )
    notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notified_slot_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    fulfilled_appointment_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True
    )
    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    patient: Mapped["Patient"] = relationship("Patient", back_populates="waitlist_entries")
    professional: Mapped["Professional"] = relationship(
        "Professional", back_populates="waitlist_entries"
    )

    @property
    def is_open(self) -> bool:
        return self.status in {WaitlistStatus.WAITING, WaitlistStatus.NOTIFIED}

    def matches_slot(self, slot_start: datetime) -> bool:
        """A entrada cobre o horario liberado?"""
        if slot_start.date() != self.desired_date:
            return False
        moment = slot_start.time()
        if self.preferred_start_time and moment < self.preferred_start_time:
            return False
        if self.preferred_end_time and moment >= self.preferred_end_time:
            return False
        return True
