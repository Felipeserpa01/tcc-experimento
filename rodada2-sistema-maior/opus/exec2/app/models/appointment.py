"""Consultas e lista de espera."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin
from app.models.enums import AppointmentStatus, WaitlistStatus
from app.models.patient import Patient
from app.models.professional import Professional
from app.models.types import enum_type

if TYPE_CHECKING:
    from app.models.clinical import ExamRequest, MedicalRecord, Prescription


class Appointment(TimestampMixin, Base):
    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint("start_at < end_at", name="ck_appointment_interval"),
        Index("ix_appointments_professional_start", "professional_id", "start_at"),
        Index("ix_appointments_patient_start", "patient_id", "start_at"),
        # Garantia no banco contra duas consultas ativas do mesmo médico no mesmo horário
        # (protege contra condições de corrida entre requisições simultâneas).
        Index(
            "uq_appointments_professional_active_slot",
            "professional_id",
            "start_at",
            unique=True,
            sqlite_where=text("status IN ('agendada', 'confirmada', 'em_andamento')"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="RESTRICT"))
    professional_id: Mapped[int] = mapped_column(ForeignKey("professionals.id", ondelete="RESTRICT"))
    start_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[AppointmentStatus] = mapped_column(
        enum_type(AppointmentStatus), default=AppointmentStatus.SCHEDULED, index=True
    )
    reason: Mapped[str | None] = mapped_column(String(500))
    cancellation_reason: Mapped[str | None] = mapped_column(String(500))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancelled_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    no_show_at: Mapped[datetime | None] = mapped_column(DateTime)
    reschedule_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    patient: Mapped[Patient] = relationship(lazy="joined")
    professional: Mapped[Professional] = relationship(lazy="joined")
    medical_record: Mapped["MedicalRecord | None"] = relationship(back_populates="appointment", uselist=False)
    prescriptions: Mapped[list["Prescription"]] = relationship(order_by="Prescription.id")
    exams: Mapped[list["ExamRequest"]] = relationship(order_by="ExamRequest.id")

    @property
    def patient_name(self) -> str:
        return self.patient.full_name

    @property
    def professional_name(self) -> str:
        return self.professional.full_name

    @property
    def specialty(self) -> str | None:
        return self.professional.specialty


class WaitlistEntry(TimestampMixin, Base):
    """Paciente aguardando a liberação de um horário específico de um médico."""

    __tablename__ = "waitlist_entries"
    __table_args__ = (Index("ix_waitlist_professional_start", "professional_id", "desired_start_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    professional_id: Mapped[int] = mapped_column(ForeignKey("professionals.id", ondelete="CASCADE"))
    desired_start_at: Mapped[datetime] = mapped_column(DateTime)
    desired_end_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[WaitlistStatus] = mapped_column(
        enum_type(WaitlistStatus), default=WaitlistStatus.WAITING, index=True
    )
    notes: Mapped[str | None] = mapped_column(String(500))
    notified_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    patient: Mapped[Patient] = relationship(lazy="joined")
    professional: Mapped[Professional] = relationship(lazy="joined")

    @property
    def patient_name(self) -> str:
        return self.patient.full_name

    @property
    def professional_name(self) -> str:
        return self.professional.full_name
