from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import AppointmentStatus, PaymentMethod


class ReportPeriod(BaseModel):
    date_from: date
    date_to: date


class PeriodCount(BaseModel):
    period: str
    total: int


class AppointmentsByPeriodReport(BaseModel):
    period: ReportPeriod
    granularity: str
    total: int
    items: list[PeriodCount]


class ProfessionalAppointmentCount(BaseModel):
    professional_id: int
    professional_name: str
    specialty: str | None
    total: int
    completed: int
    cancelled: int
    no_show: int


class AppointmentsByProfessionalReport(BaseModel):
    period: ReportPeriod
    total: int
    items: list[ProfessionalAppointmentCount]


class SpecialtyCount(BaseModel):
    specialty: str
    total: int
    completed: int


class AppointmentsBySpecialtyReport(BaseModel):
    period: ReportPeriod
    total: int
    items: list[SpecialtyCount]


class StatusCount(BaseModel):
    status: AppointmentStatus
    total: int


class AppointmentsByStatusReport(BaseModel):
    period: ReportPeriod
    total: int
    items: list[StatusCount]


class PaymentMethodRevenue(BaseModel):
    payment_method: PaymentMethod
    total: Decimal
    count: int


class PeriodRevenue(BaseModel):
    period: str
    total: Decimal
    count: int


class RevenueReport(BaseModel):
    period: ReportPeriod
    granularity: str
    total_received: Decimal
    total_discounts: Decimal
    paid_count: int
    pending_total: Decimal
    pending_count: int
    by_payment_method: list[PaymentMethodRevenue]
    by_period: list[PeriodRevenue]


class NoShowRate(BaseModel):
    professional_id: int
    professional_name: str
    specialty: str | None
    completed: int
    no_show: int
    no_show_rate: Decimal


class NoShowReport(BaseModel):
    period: ReportPeriod
    overall_rate: Decimal
    items: list[NoShowRate]


class TopPatient(BaseModel):
    patient_id: int
    patient_name: str
    total_appointments: int


class TopPatientsReport(BaseModel):
    period: ReportPeriod
    items: list[TopPatient]
