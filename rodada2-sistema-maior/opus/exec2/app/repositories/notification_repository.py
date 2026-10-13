from datetime import datetime
from typing import Any, ClassVar

from sqlalchemy import ColumnElement, select, update

from app.core.pagination import PageParams, PageResult, SortParams
from app.models.notification import Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    model = Notification
    sortable_columns: ClassVar[dict[str, Any]] = {"created_at": Notification.created_at}

    def search_for_recipient(
        self,
        page: PageParams,
        sort: SortParams,
        *,
        user_id: int,
        patient_id: int | None,
        unread_only: bool = False,
    ) -> PageResult[Notification]:
        stmt = select(Notification).where(self._recipient_filter(user_id, patient_id))
        if unread_only:
            stmt = stmt.where(Notification.read_at.is_(None))
        return self.paginate(stmt, page, sort)

    def get_for_recipient(self, notification_id: int, user_id: int, patient_id: int | None) -> Notification | None:
        return self.db.scalar(
            select(Notification).where(Notification.id == notification_id, self._recipient_filter(user_id, patient_id))
        )

    def mark_all_read(self, user_id: int, patient_id: int | None, when: datetime) -> None:
        self.db.execute(
            update(Notification)
            .where(self._recipient_filter(user_id, patient_id), Notification.read_at.is_(None))
            .values(read_at=when)
        )

    @staticmethod
    def _recipient_filter(user_id: int, patient_id: int | None) -> ColumnElement[bool]:
        if patient_id is None:
            return Notification.user_id == user_id
        return (Notification.user_id == user_id) | (Notification.patient_id == patient_id)
