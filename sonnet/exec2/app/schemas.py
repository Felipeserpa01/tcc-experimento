from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import UserRole

# ---------- User / Auth ----------


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    role: UserRole = UserRole.READER


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    role: UserRole
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int | None = None


# ---------- Book ----------


class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    author: str = Field(min_length=1, max_length=255)
    isbn: str = Field(min_length=1, max_length=20)
    year: int = Field(ge=0, le=date.today().year)
    total_copies: int = Field(ge=1)


class BookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    author: str | None = Field(default=None, min_length=1, max_length=255)
    isbn: str | None = Field(default=None, min_length=1, max_length=20)
    year: int | None = Field(default=None, ge=0, le=date.today().year)
    total_copies: int | None = Field(default=None, ge=1)


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str
    isbn: str
    year: int
    total_copies: int
    available_copies: int


# ---------- Loan ----------


class LoanCreate(BaseModel):
    book_id: int
    reader_id: int


class LoanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    reader_id: int
    loan_date: date
    due_date: date
    return_date: date | None
    fine: float | None


class LoanReturnOut(LoanOut):
    days_late: int = 0
