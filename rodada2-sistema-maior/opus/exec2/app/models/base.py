"""Mixins compartilhados pelos modelos."""

from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.core import clock


def current_time() -> datetime:
    return clock.now()


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=current_time, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=current_time, onupdate=current_time, nullable=False)
