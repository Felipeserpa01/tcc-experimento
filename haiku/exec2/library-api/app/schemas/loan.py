from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class LoanCreate(BaseModel):
    book_id: int


class LoanReturn(BaseModel):
    return_date: datetime


class LoanResponse(BaseModel):
    id: int
    book_id: int
    reader_id: int
    loan_date: datetime
    due_date: datetime
    return_date: Optional[datetime] = None
    fine: float

    class Config:
        from_attributes = True
