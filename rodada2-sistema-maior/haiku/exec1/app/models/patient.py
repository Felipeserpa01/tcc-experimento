from datetime import datetime
from sqlalchemy import Column, Integer, String, Date, Enum, ForeignKey, Text, Boolean, DateTime
from sqlalchemy.orm import relationship

from app.db.base import DeclarativeBase


class Sex(str):
    MALE = "M"
    FEMALE = "F"
    OTHER = "O"


class Patient(DeclarativeBase):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    cpf = Column(String(11), unique=True, index=True, nullable=False)
    birth_date = Column(Date, nullable=False)
    sex = Column(String(1), nullable=False)  # M, F, O
    phone = Column(String(20), nullable=True)
    address_street = Column(String(255), nullable=True)
    address_number = Column(String(20), nullable=True)
    address_complement = Column(String(255), nullable=True)
    address_neighborhood = Column(String(255), nullable=True)
    address_city = Column(String(100), nullable=True)
    address_state = Column(String(2), nullable=True)
    address_zip_code = Column(String(10), nullable=True)
    insurance_plan = Column(String(100), nullable=True)
    insurance_number = Column(String(50), nullable=True)
    allergies = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="patient")
    appointments = relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")
    waitlist_entries = relationship("WaitlistEntry", back_populates="patient", cascade="all, delete-orphan")
    charges = relationship("Charge", back_populates="patient", cascade="all, delete-orphan")
