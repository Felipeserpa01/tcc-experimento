from sqlalchemy import Column, Integer, String, Enum
from app.database import Base
import enum


class UserRole(str, enum.Enum):
    LIBRARIAN = "librarian"
    READER = "reader"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    hashed_password = Column(String)
    role = Column(Enum(UserRole), default=UserRole.READER)
    is_active = Column(Integer, default=1)
