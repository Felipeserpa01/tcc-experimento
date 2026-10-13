"""Patient schemas."""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.validators import clean_digits, is_valid_cpf


class PatientBase(BaseModel):
    nome: str = Field(min_length=3, max_length=255)
    cpf: str
    data_nascimento: date
    sexo: str = Field(max_length=20)
    telefone: str = Field(min_length=8, max_length=20)
    email: EmailStr
    endereco_rua: str = Field(max_length=255)
    endereco_numero: str = Field(max_length=20)
    endereco_complemento: str | None = Field(default=None, max_length=255)
    endereco_bairro: str = Field(max_length=255)
    endereco_cidade: str = Field(max_length=255)
    endereco_estado: str = Field(min_length=2, max_length=2)
    endereco_cep: str = Field(min_length=8, max_length=9)
    convenio: str | None = Field(default=None, max_length=255)
    alergias: str | None = None
    observacoes: str | None = None

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, value: str) -> str:
        digits = clean_digits(value)
        if not is_valid_cpf(digits):
            raise ValueError("CPF inválido.")
        return digits

    @field_validator("data_nascimento")
    @classmethod
    def validate_birthdate(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Data de nascimento não pode ser no futuro.")
        return value

    @field_validator("endereco_estado")
    @classmethod
    def validate_uf(cls, value: str) -> str:
        return value.upper()


class PatientCreate(PatientBase):
    user_id: int | None = Field(
        default=None,
        description=(
            "ID do usuário (perfil paciente) previamente registrado em /auth/register a ser "
            "vinculado a este cadastro clínico. Opcional: um paciente pode ser cadastrado sem "
            "conta de acesso própria."
        ),
    )


class PatientUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=3, max_length=255)
    telefone: str | None = Field(default=None, min_length=8, max_length=20)
    email: EmailStr | None = None
    endereco_rua: str | None = Field(default=None, max_length=255)
    endereco_numero: str | None = Field(default=None, max_length=20)
    endereco_complemento: str | None = Field(default=None, max_length=255)
    endereco_bairro: str | None = Field(default=None, max_length=255)
    endereco_cidade: str | None = Field(default=None, max_length=255)
    endereco_estado: str | None = Field(default=None, min_length=2, max_length=2)
    endereco_cep: str | None = Field(default=None, min_length=8, max_length=9)
    convenio: str | None = None
    alergias: str | None = None
    observacoes: str | None = None


class PatientOut(PatientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    created_at: datetime
    updated_at: datetime
