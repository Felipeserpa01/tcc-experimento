from __future__ import annotations

import enum
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.user import User


class LoanStatus(enum.StrEnum):
    ACTIVE = "active"
    OVERDUE = "overdue"
    RETURNED = "returned"


class Loan(Base):
    __tablename__ = "loans"
    __table_args__ = (
        Index("ix_loans_reader_id_returned_at", "reader_id", "returned_at"),
        CheckConstraint("fine_amount_cents >= 0", name="ck_loans_fine_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    reader_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    loan_date: Mapped[datetime] = mapped_column(UTCDateTime())
    due_date: Mapped[date] = mapped_column(Date())
    returned_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    # Valor em centavos, fixado na devolução: evita imprecisão de ponto
    # flutuante e preserva o valor mesmo que a multa diária mude depois.
    fine_amount_cents: Mapped[int] = mapped_column(default=0)

    book: Mapped[Book] = relationship(back_populates="loans")
    reader: Mapped[User] = relationship(back_populates="loans")

    @property
    def is_active(self) -> bool:
        return self.returned_at is None

    def status_on(self, today: date) -> LoanStatus:
        if self.returned_at is not None:
            return LoanStatus.RETURNED
        return LoanStatus.OVERDUE if today > self.due_date else LoanStatus.ACTIVE
