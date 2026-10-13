"""Notificacoes internas (ex.: vaga liberada na lista de espera)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.datetime_utils import now
from app.db.base import Base
from app.models.enums import NotificationType, enum_column

if TYPE_CHECKING:  # pragma: no cover
    from app.models.user import User


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        enum_column(NotificationType, length=48), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False, index=True)

    user: Mapped["User"] = relationship("User", back_populates="notifications")

    @property
    def is_read(self) -> bool:
        return self.read_at is not None
