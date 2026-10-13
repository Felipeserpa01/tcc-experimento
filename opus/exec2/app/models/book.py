from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime
from app.utils.time import utcnow

if TYPE_CHECKING:
    from app.models.loan import Loan


class Book(Base):
    __tablename__ = "books"
    __table_args__ = (
        CheckConstraint("total_quantity >= 0", name="ck_books_total_quantity_non_negative"),
        CheckConstraint("available_quantity >= 0", name="ck_books_available_quantity_non_negative"),
        CheckConstraint("available_quantity <= total_quantity", name="ck_books_available_lte_total"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    author: Mapped[str] = mapped_column(String(255))
    isbn: Mapped[str] = mapped_column(String(13), unique=True, index=True)
    year: Mapped[int]
    total_quantity: Mapped[int]
    available_quantity: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, onupdate=utcnow)

    # O histórico de empréstimos (já devolvidos) é removido junto com o livro;
    # livros com empréstimos ativos não podem ser removidos (ver book_service).
    loans: Mapped[list[Loan]] = relationship(
        back_populates="book", cascade="all, delete-orphan", passive_deletes=True
    )

    @property
    def loaned_quantity(self) -> int:
        return self.total_quantity - self.available_quantity
