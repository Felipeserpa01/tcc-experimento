"""Usuarios, tokens de sessao e tokens de recuperacao de senha."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.datetime_utils import now
from app.db.base import Base, TimestampMixin
from app.models.enums import UserRole, enum_column

if TYPE_CHECKING:  # pragma: no cover
    from app.models.notification import Notification
    from app.models.patient import Patient
    from app.models.professional import Professional


class User(Base, TimestampMixin):
    """Credencial de acesso. O perfil clinico fica em `Patient`/`Professional`."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(enum_column(UserRole), nullable=False, index=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    password_changed_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)

    patient: Mapped[Optional["Patient"]] = relationship(
        "Patient", back_populates="user", uselist=False
    )
    professional: Mapped[Optional["Professional"]] = relationship(
        "Professional", back_populates="user", uselist=False
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    password_reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(
        "PasswordResetToken", back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )

    # -- Regras de estado da conta ----------------------------------------
    @property
    def is_locked(self) -> bool:
        return self.locked_until is not None and self.locked_until > now()

    @property
    def is_staff(self) -> bool:
        return self.role != UserRole.PATIENT

    def register_failed_login(self, max_attempts: int, lockout_minutes: int) -> bool:
        """Incrementa o contador e bloqueia a conta quando o limite e atingido."""
        from datetime import timedelta

        self.failed_login_attempts = (self.failed_login_attempts or 0) + 1
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = now() + timedelta(minutes=lockout_minutes)
            return True
        return False

    def register_successful_login(self) -> None:
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login_at = now()


class RefreshToken(Base):
    """Refresh token persistido (permite revogacao e rotacao)."""

    __tablename__ = "refresh_tokens"
    __table_args__ = (Index("ix_refresh_tokens_user_active", "user_id", "revoked_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    jti: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    replaced_by_jti: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and self.expires_at > now()

    def revoke(self, replaced_by: str | None = None) -> None:
        if self.revoked_at is None:
            self.revoked_at = now()
        self.replaced_by_jti = replaced_by


class PasswordResetToken(Base):
    """Token de uso unico para recuperacao de senha."""

    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="password_reset_tokens")

    @property
    def is_usable(self) -> bool:
        return self.used_at is None and self.expires_at > now()
