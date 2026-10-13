from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import UTCDateTime, utc_now

if TYPE_CHECKING:
    from app.models.loan import Loan


class Book(Base):
    __tablename__ = "books"
    __table_args__ = (
        CheckConstraint("total_quantity >= 0", name="ck_books_total_non_negative"),
        CheckConstraint(
            "available_quantity >= 0 AND available_quantity <= total_quantity",
            name="ck_books_available_within_total",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    author: Mapped[str] = mapped_column(String(255), index=True)
    isbn: Mapped[str] = mapped_column(String(13), unique=True, index=True)
    year: Mapped[int]
    total_quantity: Mapped[int]
    available_quantity: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, onupdate=utc_now)

    # O histórico de empréstimos é removido junto com o livro; a remoção de livros
    # com empréstimos ativos é bloqueada no serviço.
    loans: Mapped[list["Loan"]] = relationship(back_populates="book", cascade="all, delete-orphan")

    @property
    def loaned_quantity(self) -> int:
        return self.total_quantity - self.available_quantity
