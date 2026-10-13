"""Log de auditoria de acoes sensiveis."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.datetime_utils import now
from app.db.base import Base
from app.models.enums import AuditStatus, enum_column

if TYPE_CHECKING:  # pragma: no cover
    from app.models.user import User


class AuditLog(Base):
    """Quem fez, o que fez e quando. Registro imutavel (somente insercao)."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_actor_time", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    user_role: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    resource_type: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[AuditStatus] = mapped_column(
        enum_column(AuditStatus), default=AuditStatus.SUCCESS, nullable=False, index=True
    )

    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    http_method: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    extra: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False, index=True)

    user: Mapped[Optional["User"]] = relationship("User")
