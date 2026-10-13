from datetime import date, datetime, time, timedelta
from typing import Any, ClassVar

from sqlalchemy import select

from app.core.pagination import PageParams, PageResult, SortParams
from app.models.audit import AuditLog
from app.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog
    sortable_columns: ClassVar[dict[str, Any]] = {"created_at": AuditLog.created_at, "action": AuditLog.action}

    def search(
        self,
        page: PageParams,
        sort: SortParams,
        *,
        user_id: int | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> PageResult[AuditLog]:
        stmt = select(AuditLog)
        if user_id is not None:
            stmt = stmt.where(AuditLog.user_id == user_id)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if entity_type:
            stmt = stmt.where(AuditLog.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(AuditLog.entity_id == entity_id)
        if date_from is not None:
            stmt = stmt.where(AuditLog.created_at >= datetime.combine(date_from, time.min))
        if date_to is not None:
            stmt = stmt.where(AuditLog.created_at < datetime.combine(date_to, time.min) + timedelta(days=1))
        return self.paginate(stmt, page, sort)
