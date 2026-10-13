from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import UTCDateTime, utc_now

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.user import User


class Loan(Base):
    __tablename__ = "loans"
    __table_args__ = (Index("ix_loans_reader_return", "reader_id", "return_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    reader_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    loan_date: Mapped[date]
    due_date: Mapped[date]
    return_date: Mapped[date | None]
    # Preenchida na devolução; enquanto o empréstimo está ativo a multa é apenas estimada.
    fine_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)

    reader: Mapped["User"] = relationship(back_populates="loans")
    book: Mapped["Book"] = relationship(back_populates="loans")

    @property
    def is_active(self) -> bool:
        return self.return_date is None
