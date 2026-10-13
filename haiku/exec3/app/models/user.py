from sqlalchemy import Column, Integer, String, Enum as SQLEnum
from app.database import Base
import enum

class UserType(str, enum.Enum):
    LIBRARIAN = "librarian"
    READER = "reader"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    user_type = Column(SQLEnum(UserType), default=UserType.READER, nullable=False)
    is_active = Column(Integer, default=1)
