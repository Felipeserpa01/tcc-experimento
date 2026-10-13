"""Repositorio do log de auditoria."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select

from app.core.datetime_utils import range_bounds
from app.core.pagination import PaginationParams
from app.models.audit import AuditLog
from app.models.enums import AuditStatus
from app.repositories.base import BaseRepository

AUDIT_SORT_FIELDS = {
    "id": AuditLog.id,
    "created_at": AuditLog.created_at,
    "action": AuditLog.action,
}


class AuditRepository(BaseRepository[AuditLog]):
    model = AuditLog

    def search(
        self,
        pagination: PaginationParams,
        *,
        user_id: int | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        status: AuditStatus | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[list[AuditLog], int]:
        stmt = select(AuditLog)
        if user_id is not None:
            stmt = stmt.where(AuditLog.user_id == user_id)
        if action:
            stmt = stmt.where(AuditLog.action.ilike(f"{action.strip()}%"))
        if resource_type:
            stmt = stmt.where(AuditLog.resource_type == resource_type)
        if resource_id:
            stmt = stmt.where(AuditLog.resource_id == str(resource_id))
        if status is not None:
            stmt = stmt.where(AuditLog.status == status)

        start, end = range_bounds(start_date, end_date)
        if start is not None:
            stmt = stmt.where(AuditLog.created_at >= start)
        if end is not None:
            stmt = stmt.where(AuditLog.created_at < end)

        column, descending = pagination.resolve_sort(AUDIT_SORT_FIELDS, "created_at")
        stmt = self.apply_order(stmt, column, descending)
        return self.paginate(stmt, pagination.page, pagination.size)
