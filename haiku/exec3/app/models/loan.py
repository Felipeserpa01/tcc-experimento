from sqlalchemy import Column, Integer, DateTime, ForeignKey, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
import enum

class LoanStatus(str, enum.Enum):
    ACTIVE = "active"
    RETURNED = "returned"
    OVERDUE = "overdue"

class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False, index=True)
    loan_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    due_date = Column(DateTime, nullable=False)
    return_date = Column(DateTime, nullable=True)
    status = Column(SQLEnum(LoanStatus), default=LoanStatus.ACTIVE, nullable=False)
    fine_amount = Column(Float, default=0.0)

    user = relationship("User")
    book = relationship("Book")
