"""Billing model."""
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.enums import BillableType, BillingStatus, PaymentMethod
from app.database import Base


class Billing(Base):
    __tablename__ = "billings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id"), nullable=True)
    exam_id: Mapped[int | None] = mapped_column(ForeignKey("exams.id"), nullable=True)

    tipo: Mapped[BillableType] = mapped_column(Enum(BillableType), nullable=False)
    valor: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    valor_desconto: Mapped[float] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    valor_final: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    convenio_aplicado: Mapped[bool] = mapped_column(default=False, nullable=False)

    forma_pagamento: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), nullable=False)
    status: Mapped[BillingStatus] = mapped_column(
        Enum(BillingStatus), default=BillingStatus.PENDENTE, nullable=False, index=True
    )

    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    patient = relationship("Patient", back_populates="billings")
    appointment = relationship("Appointment", back_populates="billings")
    exam = relationship("Exam", back_populates="billings")
