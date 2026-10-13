from datetime import datetime, date, time
from sqlalchemy import Column, Integer, Date, Time, Enum, ForeignKey, Text, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import DeclarativeBase
from app.core.enums import AppointmentStatus


class Appointment(DeclarativeBase):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("professionals.id"), nullable=False)
    scheduled_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.SCHEDULED, nullable=False)
    cancellation_reason = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('doctor_id', 'scheduled_date', 'start_time', name='unique_appointment_slot'),
    )

    # Relationships
    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Professional", back_populates="appointments", foreign_keys=[doctor_id])
    medical_record = relationship("MedicalRecord", back_populates="appointment", uselist=False, cascade="all, delete-orphan")
    prescriptions = relationship("Prescription", back_populates="appointment", cascade="all, delete-orphan")
    exams = relationship("Exam", back_populates="appointment", cascade="all, delete-orphan")
    charges = relationship("Charge", back_populates="appointment", cascade="all, delete-orphan")
