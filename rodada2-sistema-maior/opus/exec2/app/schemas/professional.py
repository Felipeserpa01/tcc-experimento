from datetime import date, datetime, time
from decimal import Decimal
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from app.models.enums import ProfessionalType
from app.schemas.common import COREN, CRM, Email, InputSchema, MoneyAmount, NonNull, OutputSchema, PersonName, Phone


class ProfessionalCreate(InputSchema):
    full_name: PersonName
    professional_type: ProfessionalType
    crm: CRM | None = Field(default=None, description="Obrigatório para médicos. Ex.: CRM/SP 123456")
    coren: COREN | None = Field(default=None, description="Obrigatório para enfermeiros. Ex.: COREN/SP 123456")
    specialty: str | None = Field(default=None, min_length=2, max_length=100)
    email: Email | None = None
    phone: Phone | None = None
    consultation_fee: MoneyAmount | None = Field(default=None, description="Valor padrão da consulta (R$)")

    @model_validator(mode="after")
    def _validate_registration(self) -> "ProfessionalCreate":
        if self.professional_type == ProfessionalType.DOCTOR:
            if not self.crm:
                raise ValueError("CRM é obrigatório para médicos.")
            if not self.specialty:
                raise ValueError("Especialidade é obrigatória para médicos.")
            if self.coren:
                raise ValueError("Médicos não possuem COREN.")
        else:
            if not self.coren:
                raise ValueError("COREN é obrigatório para enfermeiros.")
            if self.crm:
                raise ValueError("Enfermeiros não possuem CRM.")
        return self


class ProfessionalUpdate(InputSchema):
    full_name: Annotated[PersonName | None, NonNull] = None
    crm: Annotated[CRM | None, NonNull] = None
    coren: Annotated[COREN | None, NonNull] = None
    specialty: Annotated[str | None, NonNull, Field(min_length=2, max_length=100)] = None
    email: Email | None = None
    phone: Phone | None = None
    consultation_fee: MoneyAmount | None = None
    is_active: Annotated[bool | None, NonNull] = None


class ProfessionalSummary(OutputSchema):
    id: int
    full_name: str
    professional_type: ProfessionalType
    specialty: str | None


class AvailabilityOut(OutputSchema):
    id: int
    weekday: int
    weekday_name: str
    start_time: time
    end_time: time
    slot_minutes: int


class ProfessionalOut(ProfessionalSummary):
    crm: str | None
    coren: str | None
    email: str | None
    phone: str | None
    consultation_fee: Decimal | None
    is_active: bool
    user_id: int | None
    availabilities: list[AvailabilityOut]
    created_at: datetime
    updated_at: datetime


class AvailabilityCreate(InputSchema):
    weekday: int = Field(ge=0, le=6, description="0 = segunda-feira ... 6 = domingo")
    start_time: time
    end_time: time
    slot_minutes: int = Field(default=30, ge=10, le=240, description="Duração de cada consulta, em minutos")

    @field_validator("start_time", "end_time")
    @classmethod
    def _whole_minutes(cls, value: time) -> time:
        if value.second or value.microsecond or value.tzinfo:
            raise ValueError("Informe o horário no formato HH:MM, sem segundos ou fuso.")
        return value

    @model_validator(mode="after")
    def _validate_interval(self) -> "AvailabilityCreate":
        if self.start_time >= self.end_time:
            raise ValueError("O horário inicial deve ser anterior ao horário final.")
        start_minutes = self.start_time.hour * 60 + self.start_time.minute
        end_minutes = self.end_time.hour * 60 + self.end_time.minute
        if end_minutes - start_minutes < self.slot_minutes:
            raise ValueError("A faixa de horário deve comportar ao menos uma consulta completa.")
        return self


class TimeSlot(OutputSchema):
    start_at: datetime
    end_at: datetime


class AvailableSlotsOut(OutputSchema):
    professional_id: int
    date: date
    slots: list[TimeSlot]
