from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import Sex


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), unique=True, nullable=True, index=True
    )

    full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cpf: Mapped[str] = mapped_column(String(11), unique=True, nullable=False, index=True)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    sex: Mapped[Sex] = mapped_column(Enum(Sex), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    address_street: Mapped[str] = mapped_column(String(255), nullable=False)
    address_number: Mapped[str] = mapped_column(String(20), nullable=False)
    address_complement: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address_neighborhood: Mapped[str] = mapped_column(String(100), nullable=False)
    address_city: Mapped[str] = mapped_column(String(100), nullable=False)
    address_state: Mapped[str] = mapped_column(String(2), nullable=False)
    address_zip_code: Mapped[str] = mapped_column(String(10), nullable=False)

    insurance: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    allergies: Mapped[str | None] = mapped_column(Text, nullable=True)
    observations: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="patient")
    appointments: Mapped[list["Appointment"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
