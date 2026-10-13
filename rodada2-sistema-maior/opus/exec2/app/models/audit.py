"""Log de auditoria de ações sensíveis."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import current_time


class AuditLog(Base):
    """Registro imutável: quem fez, o que fez, sobre qual entidade e quando."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    user_email: Mapped[str | None] = mapped_column(String(255))
    user_role: Mapped[str | None] = mapped_column(String(20))
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(50), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(50))
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    request_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=current_time, index=True)
