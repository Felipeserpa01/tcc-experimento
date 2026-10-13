"""Schemas de auditoria e notificacoes."""

from __future__ import annotations

from datetime import datetime

from app.models.enums import AuditStatus, NotificationType
from app.schemas.common import ORMModel


class AuditLogRead(ORMModel):
    id: int
    user_id: int | None = None
    user_email: str | None = None
    user_role: str | None = None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    description: str | None = None
    status: AuditStatus
    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str | None = None
    http_method: str | None = None
    path: str | None = None
    extra: str | None = None
    created_at: datetime


class NotificationRead(ORMModel):
    id: int
    user_id: int
    notification_type: NotificationType
    title: str
    message: str
    resource_type: str | None = None
    resource_id: str | None = None
    read_at: datetime | None = None
    created_at: datetime
