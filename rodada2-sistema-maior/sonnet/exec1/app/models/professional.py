from datetime import datetime, time

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, SmallInteger, String, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import ProfessionalType


class Professional(Base):
    __tablename__ = "professionals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False, index=True)

    full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    professional_type: Mapped[ProfessionalType] = mapped_column(Enum(ProfessionalType), nullable=False)
    license_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    specialty: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="professional")
    availabilities: Mapped[list["Availability"]] = relationship(
        back_populates="professional", cascade="all, delete-orphan"
    )
    appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="doctor", cascade="all, delete-orphan"
    )


class Availability(Base):
    """Weekly recurring availability slot for a professional (0=Monday ... 6=Sunday)."""

    __tablename__ = "availabilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    professional_id: Mapped[int] = mapped_column(
        ForeignKey("professionals.id"), nullable=False, index=True
    )
    weekday: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    professional: Mapped["Professional"] = relationship(back_populates="availabilities")
