from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.models.loan import LoanStatus
from app.schemas.book import BookSummary
from app.schemas.common import Money
from app.schemas.user import UserSummary


class LoanCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"book_id": 1, "reader_id": 2, "loan_days": 14}]},
    )

    book_id: int = Field(gt=0, strict=True)
    reader_id: int = Field(gt=0, strict=True)
    loan_days: int | None = Field(
        default=None,
        ge=1,
        le=settings.max_loan_days,
        strict=True,
        description=f"Prazo do empréstimo em dias. Padrão: {settings.default_loan_days}.",
    )


class LoanRead(BaseModel):
    id: int
    book: BookSummary
    reader: UserSummary
    loan_date: datetime
    due_date: date
    returned_at: datetime | None
    status: LoanStatus
    days_overdue: int = Field(description="Dias de atraso (até a devolução ou até hoje, se em aberto).")
    fine_amount: Money = Field(
        description="Multa definitiva, se devolvido; multa acumulada até hoje, se ainda em aberto."
    )
