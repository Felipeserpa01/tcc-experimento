import enum
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    BIBLIOTECARIO = "bibliotecario"
    LEITOR = "leitor"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.LEITOR)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    loans: Mapped[list["Loan"]] = relationship(back_populates="reader")


class Book(Base):
    __tablename__ = "books"
    __table_args__ = (UniqueConstraint("isbn", name="uq_books_isbn"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    author: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    isbn: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    total_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    loans: Mapped[list["Loan"]] = relationship(back_populates="book")


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)
    reader_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    loan_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    return_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    fine_amount: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)

    book: Mapped["Book"] = relationship(back_populates="loans")
    reader: Mapped["User"] = relationship(back_populates="loans")

    @property
    def is_returned(self) -> bool:
        return self.return_date is not None
