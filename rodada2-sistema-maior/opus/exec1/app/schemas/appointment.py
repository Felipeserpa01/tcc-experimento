"""Schemas de agendamento e lista de espera."""

from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.datetime_utils import to_naive_local
from app.models.enums import AppointmentStatus, WaitlistStatus
from app.schemas.common import ORMModel
from app.schemas.patient import PatientSummary
from app.schemas.professional import ProfessionalSummary


class AppointmentCreate(BaseModel):
    patient_id: int | None = Field(
        None, description="Obrigatorio para a equipe; pacientes agendam para si mesmos"
    )
    professional_id: int
    scheduled_start: datetime
    duration_minutes: int | None = Field(None, ge=5, le=480)
    reason: str | None = Field(None, max_length=255)
    notes: str | None = Field(None, max_length=2000)

    @field_validator("scheduled_start")
    @classmethod
    def _normalize(cls, value: datetime) -> datetime:
        return to_naive_local(value)


class AppointmentReschedule(BaseModel):
    scheduled_start: datetime
    duration_minutes: int | None = Field(None, ge=5, le=480)
    reason: str | None = Field(None, max_length=255, description="Motivo da remarcacao")

    @field_validator("scheduled_start")
    @classmethod
    def _normalize(cls, value: datetime) -> datetime:
        return to_naive_local(value)


class AppointmentCancel(BaseModel):
    reason: str = Field(..., min_length=3, max_length=255, description="Motivo do cancelamento")

    @field_validator("reason")
    @classmethod
    def _strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Informe o motivo do cancelamento.")
        return value


class AppointmentUpdate(BaseModel):
    reason: str | None = Field(None, max_length=255)
    notes: str | None = Field(None, max_length=2000)


class AppointmentRead(ORMModel):
    id: int
    patient_id: int
    professional_id: int
    scheduled_start: datetime
    scheduled_end: datetime
    duration_minutes: int
    status: AppointmentStatus
    reason: str | None = None
    notes: str | None = None
    confirmed_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    cancellation_reason: str | None = None
    cancelled_by_id: int | None = None
    created_by_id: int | None = None
    rescheduled_from_id: int | None = None
    created_at: datetime
    updated_at: datetime


class AppointmentDetail(AppointmentRead):
    patient: PatientSummary | None = None
    professional: ProfessionalSummary | None = None


class DailyAgendaItem(ORMModel):
    id: int
    scheduled_start: datetime
    scheduled_end: datetime
    status: AppointmentStatus
    patient_id: int
    patient_name: str
    reason: str | None = None


class DailyAgendaResponse(BaseModel):
    professional_id: int
    professional_name: str
    date: date
    total: int
    appointments: list[DailyAgendaItem]


# ---------------------------------------------------------------------------
# Lista de espera
# ---------------------------------------------------------------------------
class WaitlistCreate(BaseModel):
    patient_id: int | None = None
    professional_id: int
    desired_date: date
    preferred_start_time: time | None = None
    preferred_end_time: time | None = None
    notes: str | None = Field(None, max_length=255)

    @model_validator(mode="after")
    def _validate(self) -> "WaitlistCreate":
        if (
            self.preferred_start_time
            and self.preferred_end_time
            and self.preferred_end_time <= self.preferred_start_time
        ):
            raise ValueError("O horario final preferido deve ser posterior ao inicial.")
        return self


class WaitlistRead(ORMModel):
    id: int
    patient_id: int
    professional_id: int
    desired_date: date
    preferred_start_time: time | None = None
    preferred_end_time: time | None = None
    status: WaitlistStatus
    notes: str | None = None
    notified_at: datetime | None = None
    notified_slot_start: datetime | None = None
    fulfilled_appointment_id: int | None = None
    created_at: datetime
