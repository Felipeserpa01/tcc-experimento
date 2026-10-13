import enum
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.book import BookSummary
from app.schemas.user import UserSummary


class LoanStatus(enum.StrEnum):
    ACTIVE = "active"
    RETURNED = "returned"


class LoanCreate(BaseModel):
    book_id: int = Field(gt=0)
    reader_id: int = Field(gt=0)
    due_date: date | None = Field(
        default=None,
        description="Data prevista de devolução. Se omitida, usa o prazo padrão da biblioteca.",
    )


class LoanRead(BaseModel):
    id: int
    book_id: int
    reader_id: int
    loan_date: date
    due_date: date
    return_date: date | None
    status: LoanStatus
    days_overdue: int = Field(description="Dias de atraso na devolução (ou até hoje, se ainda ativo)")
    fine_amount: Decimal = Field(
        description="Multa definitiva se o livro já foi devolvido; caso contrário, multa acumulada até hoje."
    )
    book: BookSummary
    reader: UserSummary


class FineRead(BaseModel):
    loan_id: int
    due_date: date
    reference_date: date = Field(description="Data de devolução ou, se ainda ativo, a data atual")
    days_overdue: int
    daily_fine: Decimal
    amount: Decimal
    is_final: bool = Field(description="True se o empréstimo já foi devolvido e a multa não muda mais")
