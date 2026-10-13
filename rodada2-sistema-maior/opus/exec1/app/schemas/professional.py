"""Schemas de profissionais e agenda de disponibilidade."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, computed_field, field_validator, model_validator

from app.models.enums import CouncilType, ProfessionalType
from app.models.professional import WEEKDAY_NAMES
from app.schemas.common import ORMModel
from app.utils.validators import normalize_council_number, normalize_phone, normalize_state


class ScheduleCreate(BaseModel):
    weekday: int = Field(..., ge=0, le=6, description="0=segunda ... 6=domingo")
    start_time: time
    end_time: time
    slot_duration_minutes: int = Field(30, ge=5, le=240)
    is_active: bool = True

    @model_validator(mode="after")
    def _validate_window(self) -> "ScheduleCreate":
        if self.end_time <= self.start_time:
            raise ValueError("O horario final deve ser posterior ao horario inicial.")
        total_minutes = (
            self.end_time.hour * 60 + self.end_time.minute
        ) - (self.start_time.hour * 60 + self.start_time.minute)
        if total_minutes < self.slot_duration_minutes:
            raise ValueError(
                "A faixa de atendimento e menor que a duracao de um atendimento."
            )
        return self


class ScheduleUpdate(BaseModel):
    weekday: int | None = Field(None, ge=0, le=6)
    start_time: time | None = None
    end_time: time | None = None
    slot_duration_minutes: int | None = Field(None, ge=5, le=240)
    is_active: bool | None = None


class ScheduleRead(ORMModel):
    id: int
    professional_id: int
    weekday: int
    start_time: time
    end_time: time
    slot_duration_minutes: int
    is_active: bool

    @computed_field  # type: ignore[prop-decorator]
    @property
    def weekday_name(self) -> str:
        return WEEKDAY_NAMES.get(self.weekday, "desconhecido")


class ProfessionalCreate(BaseModel):
    full_name: str = Field(..., min_length=3, max_length=150)
    professional_type: ProfessionalType
    council_type: CouncilType | None = Field(
        None, description="Derivado de professional_type (CRM para medico, COREN para enfermeiro)"
    )
    council_number: str = Field(..., max_length=10, description="Numero do CRM/COREN")
    council_state: str = Field(..., min_length=2, max_length=2)
    specialty: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    appointment_price: Decimal = Field(Decimal("0.00"), ge=0, le=Decimal("99999999.99"))
    appointment_duration_minutes: int = Field(30, ge=5, le=240)
    is_active: bool = True

    # Criacao opcional do login do profissional
    create_user_account: bool = False
    account_email: EmailStr | None = None
    account_password: str | None = Field(None, min_length=8, max_length=72)

    schedules: list[ScheduleCreate] = Field(default_factory=list)

    @field_validator("full_name")
    @classmethod
    def _name(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value.split(" ")) < 2:
            raise ValueError("Informe nome e sobrenome.")
        return value

    @field_validator("council_number")
    @classmethod
    def _council(cls, value: str) -> str:
        return normalize_council_number(value)

    @field_validator("council_state")
    @classmethod
    def _state(cls, value: str) -> str:
        return normalize_state(value)

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        return normalize_phone(value) if value else value

    @model_validator(mode="after")
    def _validate_rules(self) -> "ProfessionalCreate":
        expected_council = (
            CouncilType.CRM if self.professional_type == ProfessionalType.DOCTOR else CouncilType.COREN
        )
        self.council_type = expected_council
        if self.professional_type == ProfessionalType.DOCTOR and not self.specialty:
            raise ValueError("Especialidade e obrigatoria para medicos.")
        if self.create_user_account and not self.account_password:
            raise ValueError("Informe `account_password` para criar o acesso do profissional.")
        if self.create_user_account and not (self.account_email or self.email):
            raise ValueError("Informe `account_email` ou `email` para criar o acesso.")
        return self


class ProfessionalUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=3, max_length=150)
    specialty: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    council_number: str | None = Field(None, max_length=10)
    council_state: str | None = Field(None, min_length=2, max_length=2)
    appointment_price: Decimal | None = Field(None, ge=0, le=Decimal("99999999.99"))
    appointment_duration_minutes: int | None = Field(None, ge=5, le=240)
    is_active: bool | None = None

    @field_validator("full_name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value else value

    @field_validator("council_number")
    @classmethod
    def _council(cls, value: str | None) -> str | None:
        return normalize_council_number(value) if value else value

    @field_validator("council_state")
    @classmethod
    def _state(cls, value: str | None) -> str | None:
        return normalize_state(value) if value else value

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        return normalize_phone(value) if value else value


class ProfessionalRead(ORMModel):
    id: int
    user_id: int | None = None
    full_name: str
    professional_type: ProfessionalType
    council_type: CouncilType
    council_number: str
    council_state: str
    specialty: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    appointment_price: Decimal
    appointment_duration_minutes: int
    is_active: bool
    schedules: list[ScheduleRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def council_label(self) -> str:
        return f"{self.council_type.value}/{self.council_state} {self.council_number}"


class ProfessionalSummary(ORMModel):
    id: int
    full_name: str
    professional_type: ProfessionalType
    specialty: str | None = None
    council_number: str
    council_state: str
    is_active: bool


class AvailableSlot(BaseModel):
    start: datetime
    end: datetime
    available: bool


class AvailabilityResponse(BaseModel):
    professional_id: int
    date: date
    slots: list[AvailableSlot]
