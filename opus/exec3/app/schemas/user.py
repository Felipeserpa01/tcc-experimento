from typing import Annotated

from pydantic import AfterValidator, EmailStr, Field, field_validator

from app.models.user import UserRole
from app.schemas.common import InputSchema, OutputSchema, trimmed_str

Name = trimmed_str(2, 120)


def _check_password_strength(value: str) -> str:
    if not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
        raise ValueError("A senha deve conter ao menos uma letra e um número.")
    return value


Password = Annotated[str, Field(min_length=8, max_length=128), AfterValidator(_check_password_strength)]


class UserRegister(InputSchema):
    """Auto-cadastro público: sempre cria um leitor."""

    name: Name
    email: EmailStr
    password: Password

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        return value.lower()


class UserCreate(UserRegister):
    """Cadastro feito por um bibliotecário, que pode escolher o perfil."""

    role: UserRole = UserRole.READER


class UserOut(OutputSchema):
    id: int
    name: str
    email: str
    role: UserRole


class UserSummary(OutputSchema):
    id: int
    name: str
    email: str
