from datetime import date

from pydantic import BaseModel, EmailStr, field_validator

from app.core.security import PASSWORD_POLICY_MESSAGE, validate_password_policy


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    cpf: str
    birth_date: date
    sex: str
    phone: str
    address_street: str
    address_number: str
    address_complement: str | None = None
    address_neighborhood: str
    address_city: str
    address_state: str
    address_zip_code: str
    insurance: str | None = None
    allergies: str | None = None
    observations: str | None = None

    @field_validator("password")
    @classmethod
    def check_password_policy(cls, value: str) -> str:
        if not validate_password_policy(value):
            raise ValueError(PASSWORD_POLICY_MESSAGE)
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_password_policy(cls, value: str) -> str:
        if not validate_password_policy(value):
            raise ValueError(PASSWORD_POLICY_MESSAGE)
        return value


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str
    reset_token: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_password_policy(cls, value: str) -> str:
        if not validate_password_policy(value):
            raise ValueError(PASSWORD_POLICY_MESSAGE)
        return value
