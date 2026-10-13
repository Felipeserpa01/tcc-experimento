from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.user import NormalizedEmail


class LoginRequest(BaseModel):
    email: NormalizedEmail
    password: str = Field(min_length=1, max_length=256)


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description="Validade do token, em segundos.")
