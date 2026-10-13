from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import AppointmentStatus


class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    scheduled_at: datetime
    duration_minutes: int = 30


class AppointmentReschedule(BaseModel):
    scheduled_at: datetime


class AppointmentCancel(BaseModel):
    reason: str


class AppointmentStatusUpdate(BaseModel):
    status: AppointmentStatus


class AppointmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    doctor_id: int
    scheduled_at: datetime
    duration_minutes: int
    status: AppointmentStatus
    cancellation_reason: str | None
    created_at: datetime
    updated_at: datetime


class WaitListCreate(BaseModel):
    patient_id: int
    doctor_id: int
    desired_date: date


class WaitListRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    doctor_id: int
    desired_date: date
    notified: bool
    created_at: datetime
