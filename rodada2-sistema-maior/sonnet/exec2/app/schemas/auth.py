"""Auth-related schemas: register, login, tokens, password change/reset."""
from pydantic import BaseModel, EmailStr, field_validator

from app.core.enums import UserRole
from app.core.validators import is_strong_password


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    role: UserRole

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not is_strong_password(value):
            raise ValueError(
                "A senha deve ter no mínimo 8 caracteres e incluir letras, números e um símbolo."
            )
        return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not is_strong_password(value):
            raise ValueError(
                "A senha deve ter no mínimo 8 caracteres e incluir letras, números e um símbolo."
            )
        return value


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not is_strong_password(value):
            raise ValueError(
                "A senha deve ter no mínimo 8 caracteres e incluir letras, números e um símbolo."
            )
        return value
