from datetime import datetime, time
from sqlalchemy import Column, Integer, Time, ForeignKey, DateTime, Enum, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import DeclarativeBase
from app.core.enums import Weekday


class AvailabilitySlot(DeclarativeBase):
    __tablename__ = "availability_slots"

    id = Column(Integer, primary_key=True, index=True)
    professional_id = Column(Integer, ForeignKey("professionals.id"), nullable=False)
    weekday = Column(Enum(Weekday), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('professional_id', 'weekday', 'start_time', 'end_time', name='unique_availability_slot'),
    )

    # Relationships
    professional = relationship("Professional", back_populates="availability_slots")
