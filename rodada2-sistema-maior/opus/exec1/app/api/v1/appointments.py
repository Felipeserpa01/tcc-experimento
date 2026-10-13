"""Rotas de agendamento de consultas e lista de espera."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.pagination import Page, PaginationParams
from app.db.session import get_db
from app.models.enums import AppointmentStatus, WaitlistStatus
from app.models.user import User
from app.schemas.appointment import (
    AppointmentCancel,
    AppointmentCreate,
    AppointmentRead,
    AppointmentReschedule,
    AppointmentUpdate,
    WaitlistCreate,
    WaitlistRead,
)
from app.services.appointment_service import AppointmentService

router = APIRouter(prefix="/appointments", tags=["Agendamento"])
waitlist_router = APIRouter(prefix="/waitlist", tags=["Lista de espera"])


@router.post(
    "",
    response_model=AppointmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Agenda uma consulta",
    description=(
        "Valida conflito de horario do medico, disponibilidade cadastrada na agenda, "
        "agendamento no passado e conflito na agenda do proprio paciente."
    ),
)
def create_appointment(
    payload: AppointmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AppointmentRead:
    return AppointmentRead.model_validate(AppointmentService(db).create(payload, current_user))


@router.get(
    "",
    response_model=Page[AppointmentRead],
    summary="Lista consultas com filtros, paginacao e ordenacao",
)
def list_appointments(
    pagination: PaginationParams = Depends(),
    patient_id: int | None = Query(None),
    professional_id: int | None = Query(None),
    appointment_status: AppointmentStatus | None = Query(None, alias="status"),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[AppointmentRead]:
    items, total = AppointmentService(db).search(
        pagination,
        current_user,
        patient_id=patient_id,
        professional_id=professional_id,
        status=appointment_status,
        start_date=start_date,
        end_date=end_date,
    )
    return Page.create(
        [AppointmentRead.model_validate(item) for item in items],
        total,
        pagination.page,
        pagination.size,
    )


@router.get("/{appointment_id}", response_model=AppointmentRead, summary="Detalha uma consulta")
def get_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AppointmentRead:
    return AppointmentRead.model_validate(
        AppointmentService(db).get(appointment_id, current_user)
    )


@router.patch(
    "/{appointment_id}", response_model=AppointmentRead, summary="Atualiza motivo/observacoes"
)
def update_appointment(
    appointment_id: int,
    payload: AppointmentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AppointmentRead:
    return AppointmentRead.model_validate(
        AppointmentService(db).update_details(appointment_id, payload, current_user)
    )


@router.post(
    "/{appointment_id}/confirm", response_model=AppointmentRead, summary="Confirma a consulta"
)
def confirm_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AppointmentRead:
    return AppointmentRead.model_validate(
        AppointmentService(db).confirm(appointment_id, current_user)
    )


@router.post(
    "/{appointment_id}/cancel",
    response_model=AppointmentRead,
    summary="Cancela a consulta informando o motivo",
)
def cancel_appointment(
    appointment_id: int,
    payload: AppointmentCancel,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AppointmentRead:
    return AppointmentRead.model_validate(
        AppointmentService(db).cancel(appointment_id, payload.reason, current_user)
    )


@router.post(
    "/{appointment_id}/reschedule",
    response_model=AppointmentRead,
    summary="Remarca a consulta para um novo horario",
)
def reschedule_appointment(
    appointment_id: int,
    payload: AppointmentReschedule,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AppointmentRead:
    return AppointmentRead.model_validate(
        AppointmentService(db).reschedule(appointment_id, payload, current_user)
    )


@router.post(
    "/{appointment_id}/start",
    response_model=AppointmentRead,
    summary="Inicia o atendimento (medico responsavel)",
)
def start_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AppointmentRead:
    return AppointmentRead.model_validate(
        AppointmentService(db).start(appointment_id, current_user)
    )


@router.post(
    "/{appointment_id}/complete",
    response_model=AppointmentRead,
    summary="Conclui o atendimento (medico responsavel)",
)
def complete_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AppointmentRead:
    return AppointmentRead.model_validate(
        AppointmentService(db).complete(appointment_id, current_user)
    )


@router.post(
    "/{appointment_id}/no-show",
    response_model=AppointmentRead,
    summary="Registra falta do paciente",
)
def no_show_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AppointmentRead:
    return AppointmentRead.model_validate(
        AppointmentService(db).mark_no_show(appointment_id, current_user)
    )


# ---------------------------------------------------------------------------
# Lista de espera
# ---------------------------------------------------------------------------
@waitlist_router.post(
    "",
    response_model=WaitlistRead,
    status_code=status.HTTP_201_CREATED,
    summary="Entra na lista de espera de um profissional",
)
def join_waitlist(
    payload: WaitlistCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WaitlistRead:
    return WaitlistRead.model_validate(
        AppointmentService(db).add_to_waitlist(payload, current_user)
    )


@waitlist_router.get("", response_model=Page[WaitlistRead], summary="Lista a fila de espera")
def list_waitlist(
    pagination: PaginationParams = Depends(),
    patient_id: int | None = Query(None),
    professional_id: int | None = Query(None),
    waitlist_status: WaitlistStatus | None = Query(None, alias="status"),
    desired_date: date | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[WaitlistRead]:
    items, total = AppointmentService(db).search_waitlist(
        pagination,
        current_user,
        patient_id=patient_id,
        professional_id=professional_id,
        status=waitlist_status,
        desired_date=desired_date,
    )
    return Page.create(
        [WaitlistRead.model_validate(item) for item in items],
        total,
        pagination.page,
        pagination.size,
    )


@waitlist_router.delete(
    "/{entry_id}", response_model=WaitlistRead, summary="Sai da lista de espera"
)
def leave_waitlist(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WaitlistRead:
    return WaitlistRead.model_validate(
        AppointmentService(db).cancel_waitlist_entry(entry_id, current_user)
    )
