"""Rotas de auditoria e notificacoes."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_admin
from app.core.pagination import Page, PaginationParams
from app.db.session import get_db
from app.models.enums import AuditStatus
from app.models.user import User
from app.schemas.audit import AuditLogRead, NotificationRead
from app.schemas.common import MessageResponse
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/audit-logs", tags=["Auditoria"])
notifications_router = APIRouter(prefix="/notifications", tags=["Notificacoes"])


@router.get(
    "",
    response_model=Page[AuditLogRead],
    summary="Consulta o log de auditoria (apenas administrador)",
)
def list_audit_logs(
    pagination: PaginationParams = Depends(),
    user_id: int | None = Query(None),
    action: str | None = Query(None, description="Prefixo da acao, ex.: 'auth.' ou 'charge.'"),
    resource_type: str | None = Query(None),
    resource_id: str | None = Query(None),
    log_status: AuditStatus | None = Query(None, alias="status"),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Page[AuditLogRead]:
    items, total = AuditService(db).search(
        pagination,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        status=log_status,
        start_date=start_date,
        end_date=end_date,
    )
    return Page.create(
        [AuditLogRead.model_validate(item) for item in items],
        total,
        pagination.page,
        pagination.size,
    )


@notifications_router.get(
    "", response_model=Page[NotificationRead], summary="Notificacoes do usuario autenticado"
)
def list_notifications(
    pagination: PaginationParams = Depends(),
    only_unread: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[NotificationRead]:
    items, total = NotificationService(db).list_for_user(
        current_user, pagination, only_unread=only_unread
    )
    return Page.create(
        [NotificationRead.model_validate(item) for item in items],
        total,
        pagination.page,
        pagination.size,
    )


@notifications_router.post(
    "/{notification_id}/read", response_model=NotificationRead, summary="Marca como lida"
)
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationRead:
    service = NotificationService(db)
    notification = service.mark_read(current_user, notification_id)
    db.commit()
    return NotificationRead.model_validate(notification)


@notifications_router.post(
    "/read-all", response_model=MessageResponse, summary="Marca todas como lidas"
)
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> MessageResponse:
    service = NotificationService(db)
    updated = service.mark_all_read(current_user)
    db.commit()
    return MessageResponse(
        message="Notificacoes marcadas como lidas.", detail={"updated": updated}
    )
