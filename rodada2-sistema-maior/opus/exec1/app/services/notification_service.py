"""Notificacoes internas entregues ao usuario da clinica/paciente."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.datetime_utils import now
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.pagination import PaginationParams
from app.models.enums import NotificationType
from app.models.notification import Notification
from app.models.user import User
from app.repositories.user_repository import NotificationRepository


class NotificationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = NotificationRepository(db)

    def notify(
        self,
        *,
        user_id: int | None,
        notification_type: NotificationType,
        title: str,
        message: str,
        resource_type: str | None = None,
        resource_id: int | str | None = None,
    ) -> Notification | None:
        """Cria a notificacao. Retorna None quando o destinatario nao tem login."""
        if not user_id:
            return None
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
        )
        self.db.add(notification)
        self.db.flush()
        return notification

    def list_for_user(
        self, user: User, pagination: PaginationParams, *, only_unread: bool = False
    ) -> tuple[list[Notification], int]:
        return self.repository.list_for_user(user.id, pagination, only_unread=only_unread)

    def mark_read(self, user: User, notification_id: int) -> Notification:
        notification = self.repository.get(notification_id)
        if notification is None:
            raise NotFoundError("Notificacao nao encontrada.")
        if notification.user_id != user.id:
            raise PermissionDeniedError("Voce so pode alterar as proprias notificacoes.")
        if notification.read_at is None:
            notification.read_at = now()
            self.db.flush()
        return notification

    def mark_all_read(self, user: User) -> int:
        return self.repository.mark_all_read(user.id)

    def unread_count(self, user: User) -> int:
        return self.repository.count(user_id=user.id, read_at=None)
