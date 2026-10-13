from datetime import datetime
from typing import Any

from app.schemas.common import OutputSchema


class AuditLogOut(OutputSchema):
    id: int
    user_id: int | None
    user_email: str | None
    user_role: str | None
    action: str
    entity_type: str | None
    entity_id: str | None
    details: dict[str, Any] | None
    ip_address: str | None
    request_id: str | None
    created_at: datetime


class NotificationOut(OutputSchema):
    id: int
    subject: str
    message: str
    channel: str
    read_at: datetime | None
    created_at: datetime
