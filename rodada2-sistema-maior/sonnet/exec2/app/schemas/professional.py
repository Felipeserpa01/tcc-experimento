"""Professional and availability schemas."""
from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.core.enums import ProfessionalType
from app.core.validators import is_strong_password, is_valid_crm


class AvailabilitySlotBase(BaseModel):
    dia_semana: int = Field(ge=0, le=6, description="0=Segunda ... 6=Domingo")
    hora_inicio: time
    hora_fim: time

    @model_validator(mode="after")
    def validate_range(self) -> "AvailabilitySlotBase":
        if self.hora_fim <= self.hora_inicio:
            raise ValueError("Hora de fim deve ser posterior à hora de início.")
        return self


class AvailabilitySlotCreate(AvailabilitySlotBase):
    pass


class AvailabilitySlotOut(AvailabilitySlotBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ProfessionalBase(BaseModel):
    nome: str = Field(min_length=3, max_length=255)
    tipo: ProfessionalType
    crm: str | None = None
    especialidade: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_medico_fields(self) -> "ProfessionalBase":
        if self.tipo == ProfessionalType.MEDICO:
            if not self.crm or not is_valid_crm(self.crm):
                raise ValueError("CRM inválido. Formato esperado: 123456-UF.")
            if not self.especialidade:
                raise ValueError("Especialidade é obrigatória para médicos.")
        return self


class ProfessionalCreate(ProfessionalBase):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not is_strong_password(value):
            raise ValueError(
                "A senha deve ter no mínimo 8 caracteres e incluir letras, números e um símbolo."
            )
        return value


class ProfessionalUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=3, max_length=255)
    especialidade: str | None = Field(default=None, max_length=255)


class ProfessionalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    nome: str
    tipo: ProfessionalType
    crm: str | None
    especialidade: str | None
    created_at: datetime
    updated_at: datetime
    availability_slots: list[AvailabilitySlotOut] = []
