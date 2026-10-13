"""Schemas de usuarios (gestao administrativa)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import UserRole
from app.schemas.common import ORMModel


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)
    full_name: str = Field(..., min_length=3, max_length=150)
    role: UserRole
    is_active: bool = True

    @field_validator("full_name")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return " ".join(value.split())


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(None, min_length=3, max_length=150)
    role: UserRole | None = None
    is_active: bool | None = None

    @field_validator("full_name")
    @classmethod
    def _normalize(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value else value


class UserRead(ORMModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    failed_login_attempts: int
    locked_until: datetime | None = None
    last_login_at: datetime | None = None
    password_changed_at: datetime
    created_at: datetime
    updated_at: datetime


class UserSummary(ORMModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
