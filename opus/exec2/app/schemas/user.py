from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

from app.core.security import BCRYPT_MAX_PASSWORD_BYTES
from app.models.user import UserRole

PASSWORD_MIN_LENGTH = 8

PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
NormalizedEmail = Annotated[EmailStr, AfterValidator(str.lower)]


class UserCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"name": "Ana Souza", "email": "ana@example.com", "password": "Senha123", "role": "reader"}
            ]
        },
    )

    name: PersonName
    email: NormalizedEmail
    password: str = Field(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=BCRYPT_MAX_PASSWORD_BYTES,
        description="Mínimo de 8 caracteres, com ao menos uma letra e um número.",
    )
    role: UserRole = Field(
        default=UserRole.READER,
        description="Cadastrar um bibliotecário exige autenticação como bibliotecário.",
    )

    @field_validator("password")
    @classmethod
    def _validate_password_strength(cls, value: str) -> str:
        if len(value.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
            raise ValueError(f"A senha deve ter no máximo {BCRYPT_MAX_PASSWORD_BYTES} bytes")
        if not any(ch.isalpha() for ch in value) or not any(ch.isdigit() for ch in value):
            raise ValueError("A senha deve conter ao menos uma letra e um número")
        return value


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: UserRole
    created_at: datetime


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
