from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import ERROR_RESPONSES, CurrentUser, Notifications, Pagination, sorting
from app.core.pagination import SortOrder, SortParams
from app.schemas.audit import NotificationOut
from app.schemas.common import Page

router = APIRouter(prefix="/notifications", tags=["Notificações"], responses=ERROR_RESPONSES)

NotificationSort = Annotated[
    SortParams, Depends(sorting("created_at", default="created_at", default_order=SortOrder.DESC))
]


@router.get("", response_model=Page[NotificationOut], summary="Minhas notificações")
def list_my_notifications(
    user: CurrentUser,
    service: Notifications,
    page: Pagination,
    sort: NotificationSort,
    unread_only: bool = False,
) -> object:
    return service.list_for_user(user, page, sort, unread_only)


@router.post("/{notification_id}/read", response_model=NotificationOut, summary="Marcar notificação como lida")
def mark_as_read(notification_id: int, user: CurrentUser, service: Notifications) -> object:
    return service.mark_as_read(user, notification_id)


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT, summary="Marcar todas como lidas")
def mark_all_as_read(user: CurrentUser, service: Notifications) -> None:
    service.mark_all_as_read(user)
