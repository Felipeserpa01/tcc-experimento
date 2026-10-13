from datetime import date, datetime
from typing import Annotated

from pydantic import Field, model_validator

from app.models.enums import AllergySeverity, Sex
from app.schemas.common import (
    CEP,
    CPF,
    BirthDate,
    Email,
    InputSchema,
    NonNull,
    OutputSchema,
    PersonName,
    Phone,
    StateCode,
)
from app.schemas.insurance import InsuranceSummary


class Allergy(InputSchema):
    substance: str = Field(min_length=2, max_length=100, description="Substância/medicamento causador")
    reaction: str | None = Field(default=None, max_length=255)
    severity: AllergySeverity | None = None
    noted_at: date | None = Field(default=None, description="Data em que a alergia foi identificada")


class Address(InputSchema):
    street: str = Field(min_length=2, max_length=150)
    number: str = Field(min_length=1, max_length=10)
    complement: str | None = Field(default=None, max_length=100)
    neighborhood: str = Field(min_length=2, max_length=100)
    city: str = Field(min_length=2, max_length=100)
    state: StateCode
    zip_code: CEP


class PatientBase(InputSchema):
    full_name: PersonName
    cpf: CPF
    birth_date: BirthDate
    sex: Sex
    phone: Phone
    email: Email | None = None
    address: Address | None = None
    insurance_id: int | None = Field(default=None, gt=0)
    insurance_card_number: str | None = Field(default=None, min_length=3, max_length=30, pattern=r"^[A-Za-z0-9.\- ]+$")
    allergies: list[Allergy] = Field(default_factory=list, max_length=50)
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _card_requires_insurance(self) -> "PatientBase":
        if self.insurance_card_number and self.insurance_id is None:
            raise ValueError("Número da carteirinha exige um convênio (insurance_id).")
        return self


class PatientCreate(PatientBase):
    pass


class PatientUpdate(InputSchema):
    """Atualização parcial. Campos obrigatórios não podem ser anulados."""

    full_name: Annotated[PersonName | None, NonNull] = None
    cpf: Annotated[CPF | None, NonNull] = None
    birth_date: Annotated[BirthDate | None, NonNull] = None
    sex: Annotated[Sex | None, NonNull] = None
    phone: Annotated[Phone | None, NonNull] = None
    email: Email | None = None
    address: Address | None = None
    insurance_id: int | None = Field(default=None, gt=0)
    insurance_card_number: str | None = Field(default=None, min_length=3, max_length=30, pattern=r"^[A-Za-z0-9.\- ]+$")
    allergies: Annotated[list[Allergy] | None, NonNull, Field(max_length=50)] = None
    notes: str | None = Field(default=None, max_length=2000)


class AllergyOut(OutputSchema):
    substance: str
    reaction: str | None = None
    severity: AllergySeverity | None = None
    noted_at: date | None = None


class AddressOut(OutputSchema):
    street: str
    number: str
    complement: str | None
    neighborhood: str
    city: str
    state: str
    zip_code: str


class PatientSummary(OutputSchema):
    id: int
    full_name: str
    cpf: str
    birth_date: date


class PatientOut(PatientSummary):
    age: int
    sex: Sex
    phone: str
    email: str | None
    address: AddressOut | None
    insurance: InsuranceSummary | None
    insurance_card_number: str | None
    allergies: list[AllergyOut]
    notes: str | None
    is_active: bool
    user_id: int | None
    created_at: datetime
    updated_at: datetime
