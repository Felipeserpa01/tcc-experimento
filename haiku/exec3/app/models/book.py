from sqlalchemy import Column, Integer, String, Text
from app.database import Base

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    author = Column(String(255), nullable=False, index=True)
    isbn = Column(String(20), unique=True, nullable=False, index=True)
    year = Column(Integer, nullable=False)
    total_quantity = Column(Integer, nullable=False, default=0)
    available_quantity = Column(Integer, nullable=False, default=0)
    description = Column(Text, nullable=True)
