"""Schemas e tipos anotados reutilizáveis."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Generic, TypeVar

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, EmailStr, Field, StringConstraints

from app.core import clock
from app.utils import validators
from app.utils.money import to_money

T = TypeVar("T")


class InputSchema(BaseModel):
    """Base dos schemas de entrada: remove espaços nas bordas e rejeita campos desconhecidos."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class OutputSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    model_config = ConfigDict(from_attributes=True)

    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class MessageResponse(BaseModel):
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


def _to_local_datetime(value: datetime) -> datetime:
    value = clock.to_clinic_naive(value)
    if value.second or value.microsecond:
        raise ValueError("Informe o horário sem segundos (ex.: 2030-01-10T14:30).")
    return value


def _lower(value: str) -> str:
    return value.lower()


def _reject_null(value: Any) -> Any:
    if value is None:
        raise ValueError("Este campo não pode ser nulo.")
    return value


Email = Annotated[EmailStr, Field(max_length=255), AfterValidator(_lower)]
CPF = Annotated[str, AfterValidator(validators.normalize_cpf)]
Phone = Annotated[str, Field(max_length=25), AfterValidator(validators.normalize_phone)]
PersonName = Annotated[
    str, StringConstraints(min_length=3, max_length=150), AfterValidator(validators.validate_person_name)
]
StrongPassword = Annotated[str, Field(max_length=128), AfterValidator(validators.validate_password_strength)]
BirthDate = Annotated[date, AfterValidator(validators.validate_birth_date)]
StateCode = Annotated[str, AfterValidator(validators.normalize_state)]
CEP = Annotated[str, AfterValidator(validators.normalize_cep)]
CRM = Annotated[str, Field(max_length=30), AfterValidator(validators.normalize_crm)]
COREN = Annotated[str, Field(max_length=30), AfterValidator(validators.normalize_coren)]
ICD10 = Annotated[str, Field(max_length=10), AfterValidator(validators.normalize_icd10)]
LocalDateTime = Annotated[datetime, AfterValidator(_to_local_datetime)]
MoneyAmount = Annotated[
    Decimal, Field(gt=0, le=Decimal("1000000"), max_digits=9, decimal_places=2), AfterValidator(to_money)
]
NonNull = BeforeValidator(_reject_null)
