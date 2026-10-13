from pydantic import BaseModel, ConfigDict
from datetime import datetime
from app.models.loan import LoanStatus

class LoanCreate(BaseModel):
    book_id: int

class LoanReturn(BaseModel):
    loan_id: int

class LoanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    book_id: int
    loan_date: datetime
    due_date: datetime
    return_date: datetime | None = None
    status: LoanStatus
    fine_amount: float

class LoanDetailResponse(LoanResponse):
    book_title: str | None = None
    user_username: str | None = None
