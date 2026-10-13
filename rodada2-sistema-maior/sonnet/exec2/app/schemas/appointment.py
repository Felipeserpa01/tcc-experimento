"""Appointment and waitlist schemas."""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import AppointmentStatus, WaitlistStatus


class AppointmentCreate(BaseModel):
    patient_id: int
    professional_id: int
    data_hora: datetime
    duracao_minutos: int = Field(default=30, ge=10, le=240)

    @field_validator("data_hora")
    @classmethod
    def validate_future(cls, value: datetime) -> datetime:
        now = datetime.now(value.tzinfo) if value.tzinfo else datetime.now()
        if value <= now:
            raise ValueError("Não é possível agendar consulta em data ou horário passado.")
        return value


class AppointmentReschedule(BaseModel):
    data_hora: datetime

    @field_validator("data_hora")
    @classmethod
    def validate_future(cls, value: datetime) -> datetime:
        now = datetime.now(value.tzinfo) if value.tzinfo else datetime.now()
        if value <= now:
            raise ValueError("Não é possível remarcar para data ou horário passado.")
        return value


class AppointmentCancel(BaseModel):
    motivo: str = Field(min_length=3, max_length=1000)


class AppointmentStatusUpdate(BaseModel):
    status: AppointmentStatus


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    professional_id: int
    data_hora: datetime
    duracao_minutos: int
    status: AppointmentStatus
    motivo_cancelamento: str | None
    created_by: int
    created_at: datetime
    updated_at: datetime


class WaitlistCreate(BaseModel):
    patient_id: int
    professional_id: int
    data_desejada: date

    @field_validator("data_desejada")
    @classmethod
    def validate_future(cls, value: date) -> date:
        if value < date.today():
            raise ValueError("Data desejada não pode ser no passado.")
        return value


class WaitlistOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    professional_id: int
    data_desejada: date
    status: WaitlistStatus
    notified_at: datetime | None
    created_at: datetime
