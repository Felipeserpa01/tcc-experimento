"""Cobranças (faturamento de consultas e exames)."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.appointment import Appointment
from app.models.base import TimestampMixin
from app.models.clinical import ExamRequest
from app.models.enums import ChargeStatus, PaymentMethod
from app.models.patient import HealthInsurance, Patient
from app.models.types import Money, Percentage, enum_type


class Charge(TimestampMixin, Base):
    __tablename__ = "charges"
    __table_args__ = (
        CheckConstraint("(appointment_id IS NOT NULL) + (exam_id IS NOT NULL) = 1", name="ck_charge_single_item"),
        CheckConstraint("gross_amount > 0", name="ck_charge_gross_positive"),
        CheckConstraint("net_amount >= 0 AND net_amount <= gross_amount", name="ck_charge_net_range"),
        # No máximo uma cobrança não cancelada por consulta/exame.
        Index(
            "uq_charges_active_appointment",
            "appointment_id",
            unique=True,
            sqlite_where=text("status != 'cancelado' AND appointment_id IS NOT NULL"),
        ),
        Index(
            "uq_charges_active_exam",
            "exam_id",
            unique=True,
            sqlite_where=text("status != 'cancelado' AND exam_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="RESTRICT"), index=True)
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id", ondelete="RESTRICT"))
    exam_id: Mapped[int | None] = mapped_column(ForeignKey("exam_requests.id", ondelete="RESTRICT"))
    description: Mapped[str] = mapped_column(String(255))
    gross_amount: Mapped[Decimal] = mapped_column(Money)
    discount_percent: Mapped[Decimal] = mapped_column(Percentage, default=Decimal("0"))
    discount_amount: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"))
    net_amount: Mapped[Decimal] = mapped_column(Money)
    payment_method: Mapped[PaymentMethod] = mapped_column(enum_type(PaymentMethod), index=True)
    status: Mapped[ChargeStatus] = mapped_column(enum_type(ChargeStatus), default=ChargeStatus.PENDING, index=True)
    insurance_id: Mapped[int | None] = mapped_column(ForeignKey("health_insurances.id", ondelete="RESTRICT"))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    paid_amount: Mapped[Decimal | None] = mapped_column(Money)
    paid_registered_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancellation_reason: Mapped[str | None] = mapped_column(String(500))
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    patient: Mapped[Patient] = relationship(lazy="joined")
    insurance: Mapped[HealthInsurance | None] = relationship(lazy="joined")
    appointment: Mapped[Appointment | None] = relationship()
    exam: Mapped[ExamRequest | None] = relationship()

    @property
    def patient_name(self) -> str:
        return self.patient.full_name

    @property
    def insurance_name(self) -> str | None:
        return self.insurance.name if self.insurance else None
