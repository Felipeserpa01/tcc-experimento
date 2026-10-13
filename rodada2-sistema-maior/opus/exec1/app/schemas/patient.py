"""Schemas de convenio e paciente."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, computed_field, field_validator

from app.core.datetime_utils import today
from app.models.enums import Gender
from app.schemas.common import ORMModel
from app.utils.validators import (
    format_cpf,
    normalize_cpf,
    normalize_phone,
    normalize_state,
    normalize_zip_code,
)


# ---------------------------------------------------------------------------
# Convenio
# ---------------------------------------------------------------------------
class HealthInsuranceCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    ans_code: str | None = Field(None, max_length=32)
    discount_percent: Decimal = Field(Decimal("0.00"), ge=0, le=100)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return " ".join(value.split())


class HealthInsuranceUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=120)
    ans_code: str | None = Field(None, max_length=32)
    discount_percent: Decimal | None = Field(None, ge=0, le=100)
    is_active: bool | None = None


class HealthInsuranceRead(ORMModel):
    id: int
    name: str
    ans_code: str | None = None
    discount_percent: Decimal
    is_active: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Endereco
# ---------------------------------------------------------------------------
class AddressPayload(BaseModel):
    address_street: str = Field(..., min_length=3, max_length=150)
    address_number: str = Field(..., min_length=1, max_length=20)
    address_complement: str | None = Field(None, max_length=80)
    address_district: str = Field(..., min_length=2, max_length=80)
    address_city: str = Field(..., min_length=2, max_length=80)
    address_state: str = Field(..., min_length=2, max_length=2)
    address_zip_code: str = Field(..., max_length=10)

    @field_validator("address_state")
    @classmethod
    def _state(cls, value: str) -> str:
        return normalize_state(value)

    @field_validator("address_zip_code")
    @classmethod
    def _zip(cls, value: str) -> str:
        return normalize_zip_code(value)


# ---------------------------------------------------------------------------
# Paciente
# ---------------------------------------------------------------------------
class PatientCreate(AddressPayload):
    full_name: str = Field(..., min_length=3, max_length=150)
    cpf: str = Field(..., description="CPF com ou sem mascara")
    birth_date: date
    gender: Gender = Gender.NOT_INFORMED
    phone: str = Field(..., max_length=20)
    email: EmailStr | None = None
    insurance_id: int | None = None
    insurance_card_number: str | None = Field(None, max_length=40)
    allergies: str | None = Field(None, max_length=2000)
    notes: str | None = Field(None, max_length=2000)

    # Criacao opcional de acesso ao portal do paciente
    create_user_account: bool = False
    account_password: str | None = Field(None, min_length=8, max_length=72)

    @field_validator("full_name")
    @classmethod
    def _name(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value.split(" ")) < 2:
            raise ValueError("Informe nome e sobrenome.")
        return value

    @field_validator("cpf")
    @classmethod
    def _cpf(cls, value: str) -> str:
        return normalize_cpf(value)

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str) -> str:
        return normalize_phone(value)

    @field_validator("birth_date")
    @classmethod
    def _birth_date(cls, value: date) -> date:
        reference = today()
        if value > reference:
            raise ValueError("Data de nascimento nao pode estar no futuro.")
        if reference.year - value.year > 130:
            raise ValueError("Data de nascimento improvavel (mais de 130 anos).")
        return value


class PatientUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=3, max_length=150)
    birth_date: date | None = None
    gender: Gender | None = None
    phone: str | None = Field(None, max_length=20)
    email: EmailStr | None = None
    address_street: str | None = Field(None, min_length=3, max_length=150)
    address_number: str | None = Field(None, min_length=1, max_length=20)
    address_complement: str | None = Field(None, max_length=80)
    address_district: str | None = Field(None, min_length=2, max_length=80)
    address_city: str | None = Field(None, min_length=2, max_length=80)
    address_state: str | None = Field(None, min_length=2, max_length=2)
    address_zip_code: str | None = Field(None, max_length=10)
    insurance_id: int | None = None
    insurance_card_number: str | None = Field(None, max_length=40)
    allergies: str | None = Field(None, max_length=2000)
    notes: str | None = Field(None, max_length=2000)
    is_active: bool | None = None

    @field_validator("full_name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value else value

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        return normalize_phone(value) if value else value

    @field_validator("address_state")
    @classmethod
    def _state(cls, value: str | None) -> str | None:
        return normalize_state(value) if value else value

    @field_validator("address_zip_code")
    @classmethod
    def _zip(cls, value: str | None) -> str | None:
        return normalize_zip_code(value) if value else value

    @field_validator("birth_date")
    @classmethod
    def _birth_date(cls, value: date | None) -> date | None:
        if value and value > today():
            raise ValueError("Data de nascimento nao pode estar no futuro.")
        return value


class PatientRead(ORMModel):
    id: int
    user_id: int | None = None
    full_name: str
    cpf: str
    birth_date: date
    gender: Gender
    phone: str
    email: EmailStr | None = None
    address_street: str
    address_number: str
    address_complement: str | None = None
    address_district: str
    address_city: str
    address_state: str
    address_zip_code: str
    insurance_id: int | None = None
    insurance_card_number: str | None = None
    insurance: HealthInsuranceRead | None = None
    allergies: str | None = None
    notes: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cpf_formatted(self) -> str:
        return format_cpf(self.cpf)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def age(self) -> int:
        reference = today()
        return (
            reference.year
            - self.birth_date.year
            - ((reference.month, reference.day) < (self.birth_date.month, self.birth_date.day))
        )


class PatientSummary(ORMModel):
    id: int
    full_name: str
    cpf: str
    birth_date: date
    phone: str
    insurance_id: int | None = None
    is_active: bool
