from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import InputSchema


class LoginRequest(InputSchema):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Validade do token em segundos")
