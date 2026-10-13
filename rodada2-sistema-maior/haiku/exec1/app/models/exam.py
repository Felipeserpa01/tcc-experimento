from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.db.base import DeclarativeBase
from app.core.enums import ExamStatus


class Exam(DeclarativeBase):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=False)
    exam_name = Column(String(255), nullable=False)
    status = Column(Enum(ExamStatus), default=ExamStatus.REQUESTED, nullable=False)
    result_text = Column(Text, nullable=True)
    requested_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    appointment = relationship("Appointment", back_populates="exams")
