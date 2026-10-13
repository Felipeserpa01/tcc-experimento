from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class AppointmentReportEntry(BaseModel):
    id: int
    patient_name: str
    doctor_name: str
    specialty: str | None
    scheduled_at: datetime
    status: str


class StatusCount(BaseModel):
    status: str
    count: int


class BillingReportEntry(BaseModel):
    period_start: date
    period_end: date
    total_amount: Decimal
    total_discount: Decimal
    total_final_amount: Decimal
    by_payment_method: dict[str, Decimal]
    by_status: dict[str, Decimal]


class NoShowRateEntry(BaseModel):
    doctor_id: int
    doctor_name: str
    total_appointments: int
    no_show_count: int
    no_show_rate: float


class TopPatientEntry(BaseModel):
    patient_id: int
    patient_name: str
    appointment_count: int
