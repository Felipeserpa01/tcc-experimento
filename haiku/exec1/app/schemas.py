from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    is_librarian: bool = False


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_librarian: bool
    created_at: datetime

    class Config:
        from_attributes = True


class BookCreate(BaseModel):
    title: str
    author: str
    isbn: str
    year: int
    total_quantity: int


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    year: Optional[int] = None
    total_quantity: Optional[int] = None


class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    isbn: str
    year: int
    total_quantity: int
    available_quantity: int
    created_at: datetime

    class Config:
        from_attributes = True


class LoanCreate(BaseModel):
    book_id: int


class LoanResponse(BaseModel):
    id: int
    user_id: int
    book_id: int
    loan_date: datetime
    due_date: datetime
    return_date: Optional[datetime] = None
    fine: float

    class Config:
        from_attributes = True


class LoanReturnRequest(BaseModel):
    return_date: datetime


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class SearchBooksResponse(BaseModel):
    books: List[BookResponse]
