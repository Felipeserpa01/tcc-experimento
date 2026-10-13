"""Schemas dos relatorios e indicadores."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import AppointmentStatus, ChargeStatus, PaymentMethod


class ReportPeriod(BaseModel):
    start_date: date | None = None
    end_date: date | None = None


class AppointmentsByProfessionalItem(BaseModel):
    professional_id: int
    professional_name: str
    specialty: str | None = None
    total: int


class AppointmentsBySpecialtyItem(BaseModel):
    specialty: str
    total: int


class AppointmentsByStatusItem(BaseModel):
    status: AppointmentStatus
    total: int
    percentage: float


class AppointmentsReport(BaseModel):
    period: ReportPeriod
    total_appointments: int
    by_status: list[AppointmentsByStatusItem] = Field(default_factory=list)
    by_professional: list[AppointmentsByProfessionalItem] = Field(default_factory=list)
    by_specialty: list[AppointmentsBySpecialtyItem] = Field(default_factory=list)


class RevenueByPaymentMethodItem(BaseModel):
    payment_method: PaymentMethod | None = None
    total_charges: int
    total_amount: Decimal


class RevenueByStatusItem(BaseModel):
    status: ChargeStatus
    total_charges: int
    total_amount: Decimal


class RevenueReport(BaseModel):
    period: ReportPeriod
    total_billed: Decimal
    total_received: Decimal
    total_pending: Decimal
    total_cancelled: Decimal
    total_discounts: Decimal
    by_payment_method: list[RevenueByPaymentMethodItem] = Field(default_factory=list)
    by_status: list[RevenueByStatusItem] = Field(default_factory=list)


class NoShowRateItem(BaseModel):
    professional_id: int
    professional_name: str
    specialty: str | None = None
    total_appointments: int
    no_show_count: int
    no_show_rate_percent: float


class NoShowReport(BaseModel):
    period: ReportPeriod
    overall_total: int
    overall_no_show: int
    overall_rate_percent: float
    by_professional: list[NoShowRateItem] = Field(default_factory=list)


class TopPatientItem(BaseModel):
    patient_id: int
    patient_name: str
    total_appointments: int
    completed_appointments: int
    last_appointment_at: date | None = None


class TopPatientsReport(BaseModel):
    period: ReportPeriod
    items: list[TopPatientItem] = Field(default_factory=list)
