"""User schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.core.enums import UserRole
from app.core.validators import is_strong_password


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime


class StaffUserCreate(BaseModel):
    """Used by administrators to create receptionist/administrator accounts."""

    email: EmailStr
    password: str
    role: UserRole

    @field_validator("role")
    @classmethod
    def validate_staff_role(cls, value: UserRole) -> UserRole:
        if value not in (UserRole.ADMIN, UserRole.RECEPCIONISTA):
            raise ValueError(
                "Este endpoint cria apenas contas de administrador ou recepcionista. "
                "Médicos e enfermeiros devem ser cadastrados em /professionals."
            )
        return value

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not is_strong_password(value):
            raise ValueError(
                "A senha deve ter no mínimo 8 caracteres e incluir letras, números e um símbolo."
            )
        return value
