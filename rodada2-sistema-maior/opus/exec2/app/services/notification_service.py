"""Notificações internas + e-mail.

Os e-mails são enfileirados na sessão e enviados apenas **após o commit**: se a
transação for desfeita, nenhum e-mail é disparado.
"""

import logging

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.core import clock
from app.core.exceptions import NotFoundError
from app.core.pagination import PageParams, PageResult, SortParams
from app.models.notification import Notification
from app.models.patient import Patient
from app.models.user import User
from app.repositories.notification_repository import NotificationRepository
from app.services.email import EmailMessage, EmailSender

logger = logging.getLogger(__name__)

_PENDING_EMAILS_KEY = "pending_emails"


@event.listens_for(Session, "after_commit")
def _dispatch_pending_emails(session: Session) -> None:
    pending: list[tuple[EmailSender, EmailMessage]] = session.info.pop(_PENDING_EMAILS_KEY, [])
    for sender, message in pending:
        try:
            sender.send(message)
        except Exception:
            logger.exception("Falha ao enviar e-mail para %s", message.to)


@event.listens_for(Session, "after_rollback")
def _discard_pending_emails(session: Session) -> None:
    session.info.pop(_PENDING_EMAILS_KEY, None)


class NotificationService:
    def __init__(self, db: Session, email_sender: EmailSender) -> None:
        self.db = db
        self.email_sender = email_sender
        self.repo = NotificationRepository(db)

    def queue_email(self, to: str, subject: str, body: str) -> None:
        self.db.info.setdefault(_PENDING_EMAILS_KEY, []).append(
            (self.email_sender, EmailMessage(to=to, subject=subject, body=body))
        )

    def notify_patient(self, patient: Patient, subject: str, message: str) -> Notification:
        notification = self.repo.add(
            Notification(user_id=patient.user_id, patient_id=patient.id, subject=subject, message=message)
        )
        if email := patient.contact_email:
            self.queue_email(email, subject, message)
        return notification

    def list_for_user(
        self, user: User, page: PageParams, sort: SortParams, unread_only: bool
    ) -> PageResult[Notification]:
        return self.repo.search_for_recipient(
            page, sort, user_id=user.id, patient_id=user.patient_id, unread_only=unread_only
        )

    def mark_as_read(self, user: User, notification_id: int) -> Notification:
        notification = self.repo.get_for_recipient(notification_id, user.id, user.patient_id)
        if notification is None:
            raise NotFoundError("Notificação não encontrada.")
        if notification.read_at is None:
            notification.read_at = clock.now()
            self.db.commit()
        return notification

    def mark_all_as_read(self, user: User) -> None:
        self.repo.mark_all_read(user.id, user.patient_id, clock.now())
        self.db.commit()
