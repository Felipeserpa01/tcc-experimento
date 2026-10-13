import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base


class UserRole(str, enum.Enum):
    LIBRARIAN = "bibliotecario"
    READER = "leitor"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(
        Enum(UserRole, values_callable=lambda enum_cls: [item.value for item in enum_cls]),
        nullable=False,
        default=UserRole.READER,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    loans = relationship("Loan", back_populates="reader")


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    author = Column(String, index=True, nullable=False)
    isbn = Column(String, unique=True, index=True, nullable=False)
    year = Column(Integer, nullable=False)
    total_quantity = Column(Integer, nullable=False, default=1)
    available_quantity = Column(Integer, nullable=False, default=1)

    loans = relationship("Loan", back_populates="book")


class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    reader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    loan_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    due_date = Column(DateTime, nullable=False)
    return_date = Column(DateTime, nullable=True)
    fine_amount = Column(Float, nullable=False, default=0.0)

    book = relationship("Book", back_populates="loans")
    reader = relationship("User", back_populates="loans")
