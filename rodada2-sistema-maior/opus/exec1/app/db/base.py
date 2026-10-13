"""Declarative base e mixins comuns do ORM."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.datetime_utils import now


class Base(DeclarativeBase):
    """Base declarativa de todos os modelos."""

    def __repr__(self) -> str:  # pragma: no cover - apoio a depuracao
        identifier = getattr(self, "id", None)
        return f"<{self.__class__.__name__} id={identifier}>"


class TimestampMixin:
    """Colunas de auditoria temporal presentes em praticamente todas as tabelas."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=now, nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now, onupdate=now, nullable=False
    )
