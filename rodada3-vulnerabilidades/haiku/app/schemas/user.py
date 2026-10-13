from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole


PASSWORD_MAX_LENGTH = 128


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    # Senha não é "limpa" (sem strip): espaços no início/fim fazem parte da senha escolhida.
    password: str = Field(min_length=8, max_length=PASSWORD_MAX_LENGTH)
    role: UserRole = UserRole.READER

    @field_validator("name", "email", mode="before")
    @classmethod
    def strip_whitespace(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
            raise ValueError("A senha deve conter pelo menos uma letra e um número")
        return value


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str


class UserRead(UserSummary):
    role: UserRole
    created_at: datetime
