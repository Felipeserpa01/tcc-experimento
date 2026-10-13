from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship

from app.db.base import DeclarativeBase
from app.core.enums import ProfessionalType


class Professional(DeclarativeBase):
    __tablename__ = "professionals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    professional_type = Column(Enum(ProfessionalType), nullable=False)
    license_number = Column(String(50), unique=True, nullable=False)
    specialty = Column(String(100), nullable=True)  # Primarily for doctors
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="professional")
    availability_slots = relationship("AvailabilitySlot", back_populates="professional", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="doctor", cascade="all, delete-orphan", foreign_keys="Appointment.doctor_id")
    waitlist_entries = relationship("WaitlistEntry", back_populates="doctor", cascade="all, delete-orphan")
