from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

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

    # Remover um livro remove também seu histórico de empréstimos já devolvidos
    # (o serviço impede a remoção enquanto houver empréstimos ativos).
    loans: Mapped[list["Loan"]] = relationship(back_populates="book", cascade="all, delete-orphan")
