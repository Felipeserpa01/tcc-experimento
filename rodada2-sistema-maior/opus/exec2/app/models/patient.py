"""Pacientes e convênios."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, CheckConstraint, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core import clock
from app.core.database import Base
from app.models.base import TimestampMixin
from app.models.enums import Sex
from app.models.types import Percentage, enum_type

if TYPE_CHECKING:
    from app.models.user import User

ADDRESS_FIELDS = ("street", "number", "complement", "neighborhood", "city", "state", "zip_code")


class HealthInsurance(TimestampMixin, Base):
    """Convênio médico. O percentual de desconto é aplicado no faturamento."""

    __tablename__ = "health_insurances"
    __table_args__ = (CheckConstraint("discount_percent BETWEEN 0 AND 10000", name="ck_insurance_discount"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    ans_code: Mapped[str | None] = mapped_column(String(6), unique=True)
    discount_percent: Mapped[Decimal] = mapped_column(Percentage, default=Decimal("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Patient(TimestampMixin, Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(150), index=True)
    cpf: Mapped[str] = mapped_column(String(11), unique=True, index=True)
    birth_date: Mapped[date] = mapped_column(Date)
    sex: Mapped[Sex] = mapped_column(enum_type(Sex))
    phone: Mapped[str] = mapped_column(String(11))
    email: Mapped[str | None] = mapped_column(String(255), index=True)

    address_street: Mapped[str | None] = mapped_column(String(150))
    address_number: Mapped[str | None] = mapped_column(String(10))
    address_complement: Mapped[str | None] = mapped_column(String(100))
    address_neighborhood: Mapped[str | None] = mapped_column(String(100))
    address_city: Mapped[str | None] = mapped_column(String(100))
    address_state: Mapped[str | None] = mapped_column(String(2))
    address_zip_code: Mapped[str | None] = mapped_column(String(8))

    insurance_id: Mapped[int | None] = mapped_column(
        ForeignKey("health_insurances.id", ondelete="RESTRICT"), index=True
    )
    insurance_card_number: Mapped[str | None] = mapped_column(String(30))
    allergies: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), unique=True)

    insurance: Mapped[HealthInsurance | None] = relationship(lazy="joined")
    user: Mapped["User | None"] = relationship(back_populates="patient")

    @property
    def address(self) -> dict[str, Any] | None:
        if not self.address_street:
            return None
        return {field: getattr(self, f"address_{field}") for field in ADDRESS_FIELDS}

    def set_address(self, data: dict[str, Any] | None) -> None:
        for field in ADDRESS_FIELDS:
            setattr(self, f"address_{field}", data.get(field) if data else None)

    @property
    def age(self) -> int:
        today = clock.today()
        years = today.year - self.birth_date.year
        if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
            years -= 1
        return years

    @property
    def contact_email(self) -> str | None:
        if self.email:
            return self.email
        return self.user.email if self.user else None
