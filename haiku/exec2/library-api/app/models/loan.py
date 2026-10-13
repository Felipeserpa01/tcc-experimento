from sqlalchemy import Column, Integer, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"))
    reader_id = Column(Integer, ForeignKey("users.id"))
    loan_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime)
    return_date = Column(DateTime, nullable=True)
    fine = Column(Float, default=0.0)

    book = relationship("Book")
    reader = relationship("User")
