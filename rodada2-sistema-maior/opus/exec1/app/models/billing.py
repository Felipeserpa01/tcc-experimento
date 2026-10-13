"""Faturamento: cobrancas de consultas e exames."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import ChargeStatus, ChargeType, PaymentMethod, enum_column

if TYPE_CHECKING:  # pragma: no cover
    from app.models.appointment import Appointment
    from app.models.medical_record import ExamRequest
    from app.models.patient import Patient
    from app.models.user import User


class Charge(Base, TimestampMixin):
    """Cobranca gerada para uma consulta, um exame ou um servico avulso."""

    __tablename__ = "charges"
    __table_args__ = (
        CheckConstraint("gross_amount >= 0", name="ck_charge_gross_amount"),
        CheckConstraint("discount_amount >= 0", name="ck_charge_discount_amount"),
        CheckConstraint("net_amount >= 0", name="ck_charge_net_amount"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    appointment_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    exam_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("exam_requests.id", ondelete="SET NULL"), nullable=True, index=True
    )

    charge_type: Mapped[ChargeType] = mapped_column(enum_column(ChargeType), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)

    gross_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    discount_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0.00"), nullable=False
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), nullable=False
    )
    net_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    status: Mapped[ChargeStatus] = mapped_column(
        enum_column(ChargeStatus), default=ChargeStatus.PENDING, nullable=False, index=True
    )
    payment_method: Mapped[Optional[PaymentMethod]] = mapped_column(
        enum_column(PaymentMethod), nullable=True, index=True
    )
    insurance_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    paid_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    payment_reference: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    paid_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    patient: Mapped["Patient"] = relationship("Patient", back_populates="charges")
    appointment: Mapped[Optional["Appointment"]] = relationship("Appointment", back_populates="charges")
    exam: Mapped[Optional["ExamRequest"]] = relationship("ExamRequest", back_populates="charges")
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])
    paid_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[paid_by_id])

    @property
    def is_paid(self) -> bool:
        return self.status == ChargeStatus.PAID

    @property
    def is_cancelled(self) -> bool:
        return self.status == ChargeStatus.CANCELLED
