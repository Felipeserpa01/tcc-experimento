from datetime import date, datetime, timezone

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import UserRole

CURRENT_YEAR = datetime.now(timezone.utc).year


# ---------- User ----------

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    role: UserRole = UserRole.LEITOR


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    role: UserRole
    created_at: datetime


# ---------- Auth ----------

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int | None = None


# ---------- Book ----------

class BookBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    author: str = Field(min_length=1, max_length=255)
    isbn: str = Field(min_length=10, max_length=20)
    year: int

    @field_validator("year")
    @classmethod
    def validate_year(cls, value: int) -> int:
        if value < 1450 or value > CURRENT_YEAR + 1:
            raise ValueError(f"year must be between 1450 and {CURRENT_YEAR + 1}")
        return value

    @field_validator("isbn")
    @classmethod
    def validate_isbn(cls, value: str) -> str:
        cleaned = value.replace("-", "").replace(" ", "")
        if not cleaned.isdigit() or len(cleaned) not in (10, 13):
            raise ValueError("isbn must contain 10 or 13 digits")
        return value


class BookCreate(BookBase):
    total_quantity: int = Field(ge=0)


class BookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    author: str | None = Field(default=None, min_length=1, max_length=255)
    isbn: str | None = Field(default=None, min_length=10, max_length=20)
    year: int | None = None
    total_quantity: int | None = Field(default=None, ge=0)

    @field_validator("year")
    @classmethod
    def validate_year(cls, value: int | None) -> int | None:
        if value is None:
            return value
        if value < 1450 or value > CURRENT_YEAR + 1:
            raise ValueError(f"year must be between 1450 and {CURRENT_YEAR + 1}")
        return value


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str
    isbn: str
    year: int
    total_quantity: int
    available_quantity: int


# ---------- Loan ----------

class LoanCreate(BaseModel):
    book_id: int
    reader_id: int


class LoanReturnOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    reader_id: int
    loan_date: date
    due_date: date
    return_date: date | None
    fine_amount: float | None


class LoanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    reader_id: int
    loan_date: date
    due_date: date
    return_date: date | None
    fine_amount: float | None
