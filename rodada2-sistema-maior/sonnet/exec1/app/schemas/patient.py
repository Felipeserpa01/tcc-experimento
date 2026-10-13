from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.models.enums import Sex
from app.utils.cpf_validator import is_valid_cpf


class PatientBase(BaseModel):
    full_name: str
    cpf: str
    birth_date: date
    sex: Sex
    phone: str
    email: EmailStr | None = None
    address_street: str
    address_number: str
    address_complement: str | None = None
    address_neighborhood: str
    address_city: str
    address_state: str
    address_zip_code: str
    insurance: str | None = None
    allergies: str | None = None
    observations: str | None = None

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, value: str) -> str:
        if not is_valid_cpf(value):
            raise ValueError("CPF inválido.")
        return "".join(filter(str.isdigit, value))

    @field_validator("address_state")
    @classmethod
    def validate_state(cls, value: str) -> str:
        if len(value) != 2:
            raise ValueError("UF deve conter 2 letras.")
        return value.upper()


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    address_street: str | None = None
    address_number: str | None = None
    address_complement: str | None = None
    address_neighborhood: str | None = None
    address_city: str | None = None
    address_state: str | None = None
    address_zip_code: str | None = None
    insurance: str | None = None
    allergies: str | None = None
    observations: str | None = None


class PatientRead(PatientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    created_at: datetime
    updated_at: datetime
