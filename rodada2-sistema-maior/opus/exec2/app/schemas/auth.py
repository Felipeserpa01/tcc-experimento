from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.enums import Role
from app.schemas.common import Email, InputSchema, OutputSchema, StrongPassword
from app.schemas.patient import PatientBase


class LoginRequest(InputSchema):
    email: Email
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Validade do access token, em segundos")
    refresh_expires_in: int = Field(description="Validade do refresh token, em segundos")


class RefreshRequest(InputSchema):
    refresh_token: str = Field(min_length=20, max_length=2048)


class ChangePasswordRequest(InputSchema):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: StrongPassword

    @model_validator(mode="after")
    def _must_differ(self) -> "ChangePasswordRequest":
        if self.current_password == self.new_password:
            raise ValueError("A nova senha deve ser diferente da senha atual.")
        return self


class ForgotPasswordRequest(InputSchema):
    email: Email


class ResetPasswordRequest(InputSchema):
    token: str = Field(min_length=20, max_length=256)
    new_password: StrongPassword


class RegisterRequest(PatientBase):
    """Autocadastro público: cria um usuário com perfil *paciente* e sua ficha cadastral."""

    email: Email  # obrigatório no autocadastro
    password: StrongPassword


class CurrentUserOut(OutputSchema):
    id: int
    email: str
    full_name: str
    role: Role
    is_active: bool
    patient_id: int | None
    professional_id: int | None
    last_login_at: datetime | None
    created_at: datetime
