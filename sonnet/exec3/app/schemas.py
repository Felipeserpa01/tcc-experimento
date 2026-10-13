from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .models import UserRole


def _validate_isbn(value: Optional[str]) -> Optional[str]:
    if value is None:
        return value
    cleaned = value.replace("-", "").replace(" ", "")
    if not cleaned.isdigit() or len(cleaned) not in (10, 13):
        raise ValueError("ISBN deve conter 10 ou 13 dígitos numéricos")
    return cleaned


# ---------- Usuário / Autenticação ----------
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=72)
    role: UserRole = UserRole.READER


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: UserRole
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Livros ----------
class BookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    author: str = Field(..., min_length=1, max_length=255)
    isbn: str = Field(..., min_length=10, max_length=17)
    year: int = Field(..., ge=1000, le=2100)
    total_quantity: int = Field(..., ge=0)

    @field_validator("isbn")
    @classmethod
    def validate_isbn(cls, v: str) -> str:
        return _validate_isbn(v)


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    author: Optional[str] = Field(None, min_length=1, max_length=255)
    isbn: Optional[str] = Field(None, min_length=10, max_length=17)
    year: Optional[int] = Field(None, ge=1000, le=2100)
    total_quantity: Optional[int] = Field(None, ge=0)

    @field_validator("isbn")
    @classmethod
    def validate_isbn(cls, v: Optional[str]) -> Optional[str]:
        return _validate_isbn(v)


class BookOut(BookBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    available_quantity: int


# ---------- Empréstimos ----------
class LoanCreate(BaseModel):
    book_id: int
    reader_id: int


class LoanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    reader_id: int
    loan_date: datetime
    due_date: datetime
    return_date: Optional[datetime] = None
    fine_amount: float
