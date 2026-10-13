from datetime import datetime
from sqlalchemy import Column, Integer, Float, Enum, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship

from app.db.base import DeclarativeBase
from app.core.enums import PaymentStatus, PaymentMethod


class Charge(DeclarativeBase):
    __tablename__ = "charges"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=True)
    amount = Column(Float, nullable=False)
    discount_amount = Column(Float, default=0.0)
    final_amount = Column(Float, nullable=False)
    payment_method = Column(Enum(PaymentMethod), nullable=True)
    insurance_applied = Column(Boolean, default=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    patient = relationship("Patient", back_populates="charges")
    appointment = relationship("Appointment", back_populates="charges")
    exam = relationship("Exam")
    payments = relationship("Payment", back_populates="charge", cascade="all, delete-orphan")


class Payment(DeclarativeBase):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    charge_id = Column(Integer, ForeignKey("charges.id"), nullable=False)
    amount_paid = Column(Float, nullable=False)
    paid_at = Column(DateTime, default=datetime.utcnow)
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    charge = relationship("Charge", back_populates="payments")
