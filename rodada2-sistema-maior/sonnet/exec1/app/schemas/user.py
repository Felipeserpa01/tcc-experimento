from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.core.security import PASSWORD_POLICY_MESSAGE, validate_password_policy
from app.models.enums import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: UserRole

    @field_validator("password")
    @classmethod
    def check_password_policy(cls, value: str) -> str:
        if not validate_password_policy(value):
            raise ValueError(PASSWORD_POLICY_MESSAGE)
        return value

    @field_validator("role")
    @classmethod
    def role_must_be_staff(cls, value: UserRole) -> UserRole:
        if value == UserRole.PATIENT:
            raise ValueError("Use o endpoint de registro público para criar pacientes.")
        return value


class UserUpdate(BaseModel):
    is_active: bool | None = None
    role: UserRole | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime
