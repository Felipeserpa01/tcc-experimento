"""Professional (doctor/nurse) and availability schedule models."""
from datetime import datetime, time

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.enums import ProfessionalType
from app.database import Base


class Professional(Base):
    __tablename__ = "professionals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo: Mapped[ProfessionalType] = mapped_column(Enum(ProfessionalType), nullable=False)
    crm: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True, index=True)
    especialidade: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="professional_profile", foreign_keys=[user_id])
    availability_slots = relationship(
        "AvailabilitySlot", back_populates="professional", cascade="all, delete-orphan"
    )
    appointments = relationship("Appointment", back_populates="professional")
    waitlist_entries = relationship("WaitlistEntry", back_populates="professional")


class AvailabilitySlot(Base):
    """A recurring weekly availability window for a professional."""

    __tablename__ = "availability_slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    professional_id: Mapped[int] = mapped_column(
        ForeignKey("professionals.id", ondelete="CASCADE"), nullable=False
    )
    dia_semana: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Monday ... 6=Sunday
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    hora_fim: Mapped[time] = mapped_column(Time, nullable=False)

    professional = relationship("Professional", back_populates="availability_slots")
