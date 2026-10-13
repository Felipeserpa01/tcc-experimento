from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator

from app.core.security import PASSWORD_POLICY_MESSAGE, validate_password_policy
from app.models.enums import ProfessionalType
from app.utils.crm_validator import is_valid_license_number


class ProfessionalBase(BaseModel):
    full_name: str
    professional_type: ProfessionalType
    license_number: str
    specialty: str | None = None

    @field_validator("license_number")
    @classmethod
    def validate_license(cls, value: str) -> str:
        if not is_valid_license_number(value):
            raise ValueError("Número de registro profissional inválido. Formato esperado: 123456-UF.")
        return value.strip().upper()

    @model_validator(mode="after")
    def doctor_requires_specialty(self):
        if self.professional_type == ProfessionalType.DOCTOR and not self.specialty:
            raise ValueError("Especialidade é obrigatória para médicos.")
        return self


class ProfessionalCreate(ProfessionalBase):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def check_password_policy(cls, value: str) -> str:
        if not validate_password_policy(value):
            raise ValueError(PASSWORD_POLICY_MESSAGE)
        return value


class ProfessionalUpdate(BaseModel):
    full_name: str | None = None
    specialty: str | None = None


class ProfessionalRead(ProfessionalBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class AvailabilityCreate(BaseModel):
    weekday: int
    start_time: time
    end_time: time

    @field_validator("weekday")
    @classmethod
    def validate_weekday(cls, value: int) -> int:
        if value < 0 or value > 6:
            raise ValueError("weekday deve estar entre 0 (segunda) e 6 (domingo).")
        return value

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.start_time >= self.end_time:
            raise ValueError("Horário de início deve ser anterior ao horário de término.")
        return self


class AvailabilityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    professional_id: int
    weekday: int
    start_time: time
    end_time: time
