"""Medical record, prescription and exam models."""
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.enums import ExamStatus
from app.database import Base


class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    queixa: Mapped[str] = mapped_column(Text, nullable=False)
    diagnostico: Mapped[str] = mapped_column(Text, nullable=False)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    appointment = relationship("Appointment", back_populates="medical_record")


class Prescription(Base):
    __tablename__ = "prescriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False
    )
    medicamento: Mapped[str] = mapped_column(String(255), nullable=False)
    dosagem: Mapped[str] = mapped_column(String(100), nullable=False)
    frequencia: Mapped[str] = mapped_column(String(100), nullable=False)
    duracao: Mapped[str] = mapped_column(String(100), nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    appointment = relationship("Appointment", back_populates="prescriptions")


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False
    )
    tipo_exame: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ExamStatus] = mapped_column(
        Enum(ExamStatus), default=ExamStatus.SOLICITADO, nullable=False
    )
    resultado: Mapped[str | None] = mapped_column(Text, nullable=True)
    solicitado_por: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    solicitado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resultado_anexado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    appointment = relationship("Appointment", back_populates="exams")
    billings = relationship("Billing", back_populates="exam")
