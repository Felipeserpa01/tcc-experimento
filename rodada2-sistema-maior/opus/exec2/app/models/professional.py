"""Profissionais de saúde (médicos e enfermeiros) e sua agenda de disponibilidade."""

from datetime import datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, current_time
from app.models.enums import ProfessionalType
from app.models.types import Money, enum_type

if TYPE_CHECKING:
    from app.models.user import User

WEEKDAY_NAMES = ("segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo")


class Professional(TimestampMixin, Base):
    __tablename__ = "professionals"
    __table_args__ = (
        CheckConstraint(
            "(professional_type = 'medico' AND crm IS NOT NULL AND specialty IS NOT NULL)"
            " OR (professional_type = 'enfermeiro' AND coren IS NOT NULL)",
            name="ck_professional_registration",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(150), index=True)
    professional_type: Mapped[ProfessionalType] = mapped_column(enum_type(ProfessionalType), index=True)
    crm: Mapped[str | None] = mapped_column(String(20), unique=True)
    coren: Mapped[str | None] = mapped_column(String(20), unique=True)
    specialty: Mapped[str | None] = mapped_column(String(100), index=True)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(11))
    consultation_fee: Mapped[Decimal | None] = mapped_column(Money)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), unique=True)

    user: Mapped["User | None"] = relationship(back_populates="professional")
    availabilities: Mapped[list["Availability"]] = relationship(
        back_populates="professional",
        cascade="all, delete-orphan",
        order_by=lambda: (Availability.weekday, Availability.start_time),
    )

    @property
    def is_doctor(self) -> bool:
        return self.professional_type == ProfessionalType.DOCTOR


class Availability(Base):
    """Faixa semanal de atendimento (ex.: segunda-feira, 08:00-12:00, consultas de 30 min)."""

    __tablename__ = "professional_availabilities"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_availability_weekday"),
        CheckConstraint("start_time < end_time", name="ck_availability_interval"),
        CheckConstraint("slot_minutes > 0", name="ck_availability_slot"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    professional_id: Mapped[int] = mapped_column(ForeignKey("professionals.id", ondelete="CASCADE"), index=True)
    weekday: Mapped[int] = mapped_column(Integer)  # 0 = segunda-feira ... 6 = domingo
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    slot_minutes: Mapped[int] = mapped_column(Integer, default=30)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=current_time)

    professional: Mapped[Professional] = relationship(back_populates="availabilities")

    @property
    def weekday_name(self) -> str:
        return WEEKDAY_NAMES[self.weekday]
