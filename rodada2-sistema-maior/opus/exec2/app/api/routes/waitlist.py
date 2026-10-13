from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import ERROR_RESPONSES, Pagination, get_waitlist_service, require, sorting
from app.core.pagination import SortParams
from app.core.permissions import Permission
from app.models.enums import WaitlistStatus
from app.models.user import User
from app.schemas.appointment import WaitlistCreate, WaitlistOut
from app.schemas.common import Page
from app.services.waitlist_service import WaitlistService

router = APIRouter(prefix="/waitlist", tags=["Lista de espera"], responses=ERROR_RESPONSES)

Waitlist = Annotated[WaitlistService, Depends(get_waitlist_service)]
Reader = Annotated[User, Depends(require(Permission.WAITLIST_READ))]
Manager = Annotated[User, Depends(require(Permission.WAITLIST_MANAGE))]
WaitlistSort = Annotated[SortParams, Depends(sorting("created_at", "desired_start_at", default="created_at"))]


@router.post("", response_model=WaitlistOut, status_code=status.HTTP_201_CREATED, summary="Entrar na lista de espera")
def join_waitlist(data: WaitlistCreate, actor: Manager, service: Waitlist) -> object:
    """Só é permitido para horários **ocupados** dentro da agenda do médico.

    Quando o horário vagar (cancelamento/remarcação), os pacientes são notificados em ordem de chegada.
    """
    return service.join(actor, data)


@router.get("", response_model=Page[WaitlistOut], summary="Listar lista de espera")
def list_waitlist(
    actor: Reader,
    service: Waitlist,
    page: Pagination,
    sort: WaitlistSort,
    patient_id: Annotated[int | None, Query(gt=0)] = None,
    professional_id: Annotated[int | None, Query(gt=0)] = None,
    status_filter: Annotated[WaitlistStatus | None, Query(alias="status")] = None,
) -> object:
    return service.search(
        actor, page, sort, patient_id=patient_id, professional_id=professional_id, status=status_filter
    )


@router.get("/{entry_id}", response_model=WaitlistOut, summary="Detalhar registro da lista de espera")
def get_waitlist_entry(entry_id: int, actor: Reader, service: Waitlist) -> object:
    return service.get(actor, entry_id)


@router.post("/{entry_id}/cancel", response_model=WaitlistOut, summary="Sair da lista de espera")
def cancel_waitlist_entry(entry_id: int, actor: Manager, service: Waitlist) -> object:
    return service.cancel(actor, entry_id)
