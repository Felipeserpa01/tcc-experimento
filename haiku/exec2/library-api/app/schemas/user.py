from pydantic import BaseModel, EmailStr
from typing import Optional


class UserRegister(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: str = "reader"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str

    class Config:
        from_attributes = True
