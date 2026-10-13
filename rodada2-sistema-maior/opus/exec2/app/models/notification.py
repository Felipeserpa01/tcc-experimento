"""Notificações internas enviadas aos usuários/pacientes."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import current_time
from app.models.enums import NotificationChannel
from app.models.types import enum_type


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    patient_id: Mapped[int | None] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)
    channel: Mapped[NotificationChannel] = mapped_column(
        enum_type(NotificationChannel), default=NotificationChannel.SYSTEM
    )
    subject: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    read_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=current_time, index=True)
