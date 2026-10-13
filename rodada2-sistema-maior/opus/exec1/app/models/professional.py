"""Profissionais de saude e sua agenda de disponibilidade."""

from __future__ import annotations

from datetime import time
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import CouncilType, ProfessionalType, enum_column

if TYPE_CHECKING:  # pragma: no cover
    from app.models.appointment import Appointment, WaitlistEntry
    from app.models.user import User

WEEKDAY_NAMES = {
    0: "segunda-feira",
    1: "terca-feira",
    2: "quarta-feira",
    3: "quinta-feira",
    4: "sexta-feira",
    5: "sabado",
    6: "domingo",
}


class Professional(Base, TimestampMixin):
    """Medico ou enfermeiro. O login correspondente fica em `User`."""

    __tablename__ = "professionals"
    __table_args__ = (
        UniqueConstraint("council_type", "council_number", "council_state", name="uq_professional_council"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True
    )

    full_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    professional_type: Mapped[ProfessionalType] = mapped_column(
        enum_column(ProfessionalType), nullable=False, index=True
    )
    council_type: Mapped[CouncilType] = mapped_column(enum_column(CouncilType), nullable=False)
    council_number: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    council_state: Mapped[str] = mapped_column(String(2), nullable=False)
    specialty: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    appointment_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), nullable=False
    )
    appointment_duration_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="professional")
    schedules: Mapped[list["ProfessionalSchedule"]] = relationship(
        "ProfessionalSchedule",
        back_populates="professional",
        cascade="all, delete-orphan",
        order_by="ProfessionalSchedule.weekday, ProfessionalSchedule.start_time",
    )
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="professional", cascade="all, delete-orphan"
    )
    waitlist_entries: Mapped[list["WaitlistEntry"]] = relationship(
        "WaitlistEntry", back_populates="professional", cascade="all, delete-orphan"
    )

    @property
    def council_label(self) -> str:
        return f"{self.council_type.value}/{self.council_state} {self.council_number}"

    @property
    def is_doctor(self) -> bool:
        return self.professional_type == ProfessionalType.DOCTOR


class ProfessionalSchedule(Base, TimestampMixin):
    """Faixa de horario recorrente em que o profissional atende."""

    __tablename__ = "professional_schedules"
    __table_args__ = (
        CheckConstraint("weekday >= 0 AND weekday <= 6", name="ck_schedule_weekday"),
        CheckConstraint("slot_duration_minutes > 0", name="ck_schedule_slot_duration"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    professional_id: Mapped[int] = mapped_column(
        ForeignKey("professionals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    weekday: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    slot_duration_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    professional: Mapped["Professional"] = relationship("Professional", back_populates="schedules")

    @property
    def weekday_name(self) -> str:
        return WEEKDAY_NAMES.get(self.weekday, "desconhecido")

    def covers(self, start: time, end: time) -> bool:
        """Verifica se a faixa cobre integralmente o intervalo informado."""
        return self.is_active and self.start_time <= start and end <= self.end_time
