from datetime import date

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.book import Book
from app.models.user import User


class Loan(Base):
    __tablename__ = "loans"
    __table_args__ = (
        CheckConstraint("due_date >= loan_date", name="ck_loans_due_after_loan"),
        CheckConstraint("fine_cents >= 0", name="ck_loans_fine_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    reader_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    loan_date: Mapped[date]
    due_date: Mapped[date]
    return_date: Mapped[date | None] = mapped_column(default=None, index=True)
    # Valor monetário guardado em centavos (inteiro) para evitar erros de ponto flutuante no SQLite.
    fine_cents: Mapped[int] = mapped_column(default=0)

    book: Mapped[Book] = relationship(back_populates="loans")
    reader: Mapped[User] = relationship(back_populates="loans")

    @property
    def is_active(self) -> bool:
        return self.return_date is None
