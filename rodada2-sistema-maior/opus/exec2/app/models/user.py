"""Usuários, refresh tokens e tokens de recuperação de senha."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, current_time
from app.models.enums import Role
from app.models.types import enum_type

if TYPE_CHECKING:
    from app.models.patient import Patient
    from app.models.professional import Professional


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(enum_type(Role), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime)
    # Incrementado a cada troca/redefinição de senha ou desativação: invalida tokens emitidos antes.
    token_version: Mapped[int] = mapped_column(Integer, default=0)

    patient: Mapped["Patient | None"] = relationship(back_populates="user", uselist=False)
    professional: Mapped["Professional | None"] = relationship(back_populates="user", uselist=False)

    def is_locked(self, reference: datetime) -> bool:
        return self.locked_until is not None and self.locked_until > reference

    @property
    def patient_id(self) -> int | None:
        return self.patient.id if self.patient else None

    @property
    def professional_id(self) -> int | None:
        return self.professional.id if self.professional else None


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)
    replaced_by_jti: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=current_time)

    user: Mapped[User] = relationship()


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=current_time)

    user: Mapped[User] = relationship()
