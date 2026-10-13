"""Convenios e pacientes."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import Gender, enum_column

if TYPE_CHECKING:  # pragma: no cover
    from app.models.appointment import Appointment, WaitlistEntry
    from app.models.billing import Charge
    from app.models.medical_record import ExamRequest, MedicalRecord, Prescription
    from app.models.user import User


class HealthInsurance(Base, TimestampMixin):
    """Convenio medico, com o percentual de desconto aplicado no faturamento."""

    __tablename__ = "health_insurances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    ans_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    discount_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0.00"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    patients: Mapped[list["Patient"]] = relationship("Patient", back_populates="insurance")


class Patient(Base, TimestampMixin):
    """Cadastro completo do paciente."""

    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True
    )

    full_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    cpf: Mapped[str] = mapped_column(String(11), unique=True, nullable=False, index=True)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[Gender] = mapped_column(
        enum_column(Gender), default=Gender.NOT_INFORMED, nullable=False
    )
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # Endereco completo
    address_street: Mapped[str] = mapped_column(String(150), nullable=False)
    address_number: Mapped[str] = mapped_column(String(20), nullable=False)
    address_complement: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    address_district: Mapped[str] = mapped_column(String(80), nullable=False)
    address_city: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    address_state: Mapped[str] = mapped_column(String(2), nullable=False)
    address_zip_code: Mapped[str] = mapped_column(String(8), nullable=False)

    insurance_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("health_insurances.id", ondelete="SET NULL"), nullable=True, index=True
    )
    insurance_card_number: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)

    allergies: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="patient")
    insurance: Mapped[Optional["HealthInsurance"]] = relationship(
        "HealthInsurance", back_populates="patients"
    )
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="patient", cascade="all, delete-orphan"
    )
    medical_records: Mapped[list["MedicalRecord"]] = relationship(
        "MedicalRecord", back_populates="patient", cascade="all, delete-orphan"
    )
    prescriptions: Mapped[list["Prescription"]] = relationship(
        "Prescription", back_populates="patient", cascade="all, delete-orphan"
    )
    exam_requests: Mapped[list["ExamRequest"]] = relationship(
        "ExamRequest", back_populates="patient", cascade="all, delete-orphan"
    )
    charges: Mapped[list["Charge"]] = relationship(
        "Charge", back_populates="patient", cascade="all, delete-orphan"
    )
    waitlist_entries: Mapped[list["WaitlistEntry"]] = relationship(
        "WaitlistEntry", back_populates="patient", cascade="all, delete-orphan"
    )

    @property
    def age(self) -> int:
        from app.core.datetime_utils import today

        reference = today()
        return (
            reference.year
            - self.birth_date.year
            - ((reference.month, reference.day) < (self.birth_date.month, self.birth_date.day))
        )

    @property
    def insurance_discount_percent(self) -> Decimal:
        if self.insurance and self.insurance.is_active:
            return Decimal(self.insurance.discount_percent or 0)
        return Decimal("0.00")
