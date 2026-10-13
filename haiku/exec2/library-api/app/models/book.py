from sqlalchemy import Column, Integer, String
from app.database import Base


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    author = Column(String, index=True)
    isbn = Column(String, unique=True, index=True)
    year = Column(Integer)
    total_quantity = Column(Integer)
    available_quantity = Column(Integer)
