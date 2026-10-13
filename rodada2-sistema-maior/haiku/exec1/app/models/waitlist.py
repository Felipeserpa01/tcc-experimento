from datetime import datetime, date
from sqlalchemy import Column, Integer, Date, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.db.base import DeclarativeBase
from app.core.enums import WaitlistStatus


class WaitlistEntry(DeclarativeBase):
    __tablename__ = "waitlist_entries"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("professionals.id"), nullable=False)
    desired_date = Column(Date, nullable=True)
    status = Column(Enum(WaitlistStatus), default=WaitlistStatus.WAITING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    notified_at = Column(DateTime, nullable=True)

    # Relationships
    patient = relationship("Patient", back_populates="waitlist_entries")
    doctor = relationship("Professional", back_populates="waitlist_entries")
