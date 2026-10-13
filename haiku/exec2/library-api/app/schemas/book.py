from pydantic import BaseModel
from typing import Optional


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

    class Config:
        from_attributes = True
