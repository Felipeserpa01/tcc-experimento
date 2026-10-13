"""Patient model."""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True
    )

    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    cpf: Mapped[str] = mapped_column(String(11), unique=True, index=True, nullable=False)
    data_nascimento: Mapped[date] = mapped_column(Date, nullable=False)
    sexo: Mapped[str] = mapped_column(String(20), nullable=False)
    telefone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)

    endereco_rua: Mapped[str] = mapped_column(String(255), nullable=False)
    endereco_numero: Mapped[str] = mapped_column(String(20), nullable=False)
    endereco_complemento: Mapped[str | None] = mapped_column(String(255), nullable=True)
    endereco_bairro: Mapped[str] = mapped_column(String(255), nullable=False)
    endereco_cidade: Mapped[str] = mapped_column(String(255), nullable=False)
    endereco_estado: Mapped[str] = mapped_column(String(2), nullable=False)
    endereco_cep: Mapped[str] = mapped_column(String(9), nullable=False)

    convenio: Mapped[str | None] = mapped_column(String(255), nullable=True)
    alergias: Mapped[str | None] = mapped_column(Text, nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="patient_profile", foreign_keys=[user_id])
    appointments = relationship("Appointment", back_populates="patient")
    waitlist_entries = relationship("WaitlistEntry", back_populates="patient")
    billings = relationship("Billing", back_populates="patient")
