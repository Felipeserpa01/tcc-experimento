"""Schemas de autenticacao."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Validade do access token em segundos")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=10)


class LogoutRequest(BaseModel):
    refresh_token: str | None = Field(
        None, description="Se omitido, todas as sessoes do usuario sao encerradas"
    )
    all_sessions: bool = False


class RegisterRequest(BaseModel):
    """Auto cadastro publico: cria sempre um usuario com perfil `patient`."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)
    full_name: str = Field(..., min_length=3, max_length=150)
    cpf: str = Field(..., description="CPF do paciente (com ou sem mascara)")
    birth_date: date = Field(..., description="Data de nascimento do paciente")
    phone: str = Field(..., min_length=10, max_length=20)

    @field_validator("birth_date")
    @classmethod
    def _birth_date(cls, value: date) -> date:
        from app.core.datetime_utils import today

        if value > today():
            raise ValueError("Data de nascimento nao pode estar no futuro.")
        return value

    @field_validator("full_name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value.split(" ")) < 2:
            raise ValueError("Informe nome e sobrenome.")
        return value


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=72)

    @field_validator("new_password")
    @classmethod
    def _not_equal(cls, value: str, info) -> str:
        current = info.data.get("current_password")
        if current and current == value:
            raise ValueError("A nova senha deve ser diferente da senha atual.")
        return value


class PasswordRecoveryRequest(BaseModel):
    email: EmailStr


class PasswordRecoveryResponse(BaseModel):
    message: str
    reset_token: str | None = Field(
        None,
        description=(
            "Token de recuperacao. Exposto apenas fora de producao; "
            "em producao ele e entregue pelo canal de notificacao."
        ),
    )
    expires_at: datetime | None = None


class PasswordResetRequest(BaseModel):
    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=8, max_length=72)


class AuthenticatedUser(BaseModel):
    """Payload de `/auth/me`."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    last_login_at: datetime | None = None
    patient_id: int | None = None
    professional_id: int | None = None
