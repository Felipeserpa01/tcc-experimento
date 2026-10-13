from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_librarian = Column(Boolean, default=False)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    loans = relationship("Loan", back_populates="user")


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    author = Column(String, index=True)
    isbn = Column(String, unique=True, index=True)
    year = Column(Integer)
    total_quantity = Column(Integer)
    available_quantity = Column(Integer)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    loans = relationship("Loan", back_populates="book")


class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    book_id = Column(Integer, ForeignKey("books.id"))
    loan_date = Column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    due_date = Column(DateTime)
    return_date = Column(DateTime, nullable=True)
    fine = Column(Float, default=0.0)

    user = relationship("User", back_populates="loans")
    book = relationship("Book", back_populates="loans")
