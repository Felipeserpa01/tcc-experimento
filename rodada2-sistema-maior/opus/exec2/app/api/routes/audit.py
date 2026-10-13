from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import ERROR_RESPONSES, Pagination, get_audit_service, require, sorting
from app.core.pagination import SortOrder, SortParams
from app.core.permissions import Permission
from app.schemas.audit import AuditLogOut
from app.schemas.common import Page
from app.services.audit_service import AuditService

router = APIRouter(
    prefix="/audit-logs",
    tags=["Auditoria"],
    responses=ERROR_RESPONSES,
    dependencies=[Depends(require(Permission.AUDIT_READ))],
)

AuditSort = Annotated[
    SortParams, Depends(sorting("created_at", "action", default="created_at", default_order=SortOrder.DESC))
]


@router.get("", response_model=Page[AuditLogOut], summary="Consultar log de auditoria")
def list_audit_logs(
    service: Annotated[AuditService, Depends(get_audit_service)],
    page: Pagination,
    sort: AuditSort,
    user_id: Annotated[int | None, Query(gt=0)] = None,
    action: Annotated[str | None, Query(max_length=100, description="Ex.: auth.login.falha")] = None,
    entity_type: Annotated[str | None, Query(max_length=50)] = None,
    entity_id: Annotated[str | None, Query(max_length=50)] = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> object:
    return service.search(
        page,
        sort,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        date_from=date_from,
        date_to=date_to,
    )
