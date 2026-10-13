import enum
from datetime import date

from pydantic import Field

from app.schemas.book import BookSummary
from app.schemas.common import InputSchema, Money, OutputSchema
from app.schemas.user import UserSummary


class LoanStatus(str, enum.Enum):
    ACTIVE = "active"
    OVERDUE = "overdue"
    RETURNED = "returned"


class LoanCreate(InputSchema):
    book_id: int = Field(gt=0)
    reader_id: int = Field(gt=0)
    loan_days: int | None = Field(
        default=None, ge=1, le=90, description="Prazo em dias; se omitido, usa o prazo padrão da biblioteca."
    )


class LoanOut(OutputSchema):
    id: int
    book: BookSummary
    reader: UserSummary
    loan_date: date
    due_date: date
    return_date: date | None
    status: LoanStatus
    days_overdue: int = Field(description="Dias de atraso (até hoje, se o empréstimo ainda estiver ativo)")
    fine_amount: Money = Field(
        description="Multa definitiva para empréstimos devolvidos; valor acumulado até hoje para os ativos"
    )
