"""Rotas de profissionais, agenda de disponibilidade e slots livres."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_admin
from app.core.pagination import Page, PaginationParams
from app.db.session import get_db
from app.models.enums import ProfessionalType
from app.models.user import User
from app.schemas.appointment import DailyAgendaResponse
from app.schemas.professional import (
    AvailabilityResponse,
    ProfessionalCreate,
    ProfessionalRead,
    ProfessionalUpdate,
    ScheduleCreate,
    ScheduleRead,
    ScheduleUpdate,
)
from app.services.appointment_service import AppointmentService
from app.services.professional_service import ProfessionalService

router = APIRouter(prefix="/professionals", tags=["Profissionais"])


@router.post(
    "",
    response_model=ProfessionalRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra medico ou enfermeiro (apenas administrador)",
)
def create_professional(
    payload: ProfessionalCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProfessionalRead:
    return ProfessionalRead.model_validate(ProfessionalService(db).create(payload, current_user))


@router.get(
    "",
    response_model=Page[ProfessionalRead],
    summary="Lista profissionais (busca por nome, especialidade e tipo)",
)
def list_professionals(
    pagination: PaginationParams = Depends(),
    query: str | None = Query(None, description="Nome ou numero do conselho"),
    specialty: str | None = Query(None, description="Busca por especialidade"),
    professional_type: ProfessionalType | None = Query(None),
    is_active: bool | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[ProfessionalRead]:
    items, total = ProfessionalService(db).search(
        pagination,
        query=query,
        specialty=specialty,
        professional_type=professional_type,
        is_active=is_active,
    )
    return Page.create(
        [ProfessionalRead.model_validate(item) for item in items],
        total,
        pagination.page,
        pagination.size,
    )


@router.get("/specialties", response_model=list[str], summary="Especialidades cadastradas")
def list_specialties(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[str]:
    return ProfessionalService(db).list_specialties()


@router.get("/me", response_model=ProfessionalRead, summary="Cadastro do profissional autenticado")
def get_own_professional(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ProfessionalRead:
    return ProfessionalRead.model_validate(
        ProfessionalService(db).resolve_own_profile(current_user)
    )


@router.get("/{professional_id}", response_model=ProfessionalRead, summary="Detalha um profissional")
def get_professional(
    professional_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfessionalRead:
    return ProfessionalRead.model_validate(ProfessionalService(db).get(professional_id))


@router.patch(
    "/{professional_id}", response_model=ProfessionalRead, summary="Atualiza um profissional"
)
def update_professional(
    professional_id: int,
    payload: ProfessionalUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfessionalRead:
    return ProfessionalRead.model_validate(
        ProfessionalService(db).update(professional_id, payload, current_user)
    )


@router.delete(
    "/{professional_id}",
    response_model=ProfessionalRead,
    summary="Desativa um profissional (apenas administrador)",
)
def deactivate_professional(
    professional_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ProfessionalRead:
    return ProfessionalRead.model_validate(
        ProfessionalService(db).deactivate(professional_id, current_user)
    )


# ---------------------------------------------------------------------------
# Agenda de disponibilidade
# ---------------------------------------------------------------------------
@router.post(
    "/{professional_id}/schedules",
    response_model=ScheduleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra faixa de disponibilidade",
)
def create_schedule(
    professional_id: int,
    payload: ScheduleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScheduleRead:
    return ScheduleRead.model_validate(
        ProfessionalService(db).add_schedule(professional_id, payload, current_user)
    )


@router.get(
    "/{professional_id}/schedules",
    response_model=list[ScheduleRead],
    summary="Lista a agenda de disponibilidade do profissional",
)
def list_schedules(
    professional_id: int,
    only_active: bool = Query(False, description="Retorna apenas faixas ativas"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ScheduleRead]:
    schedules = ProfessionalService(db).list_schedules(professional_id, only_active=only_active)
    return [ScheduleRead.model_validate(item) for item in schedules]


@router.patch(
    "/{professional_id}/schedules/{schedule_id}",
    response_model=ScheduleRead,
    summary="Atualiza uma faixa de disponibilidade",
)
def update_schedule(
    professional_id: int,
    schedule_id: int,
    payload: ScheduleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScheduleRead:
    return ScheduleRead.model_validate(
        ProfessionalService(db).update_schedule(
            professional_id, schedule_id, payload, current_user
        )
    )


@router.delete(
    "/{professional_id}/schedules/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Remove uma faixa de disponibilidade",
)
def delete_schedule(
    professional_id: int,
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    ProfessionalService(db).delete_schedule(professional_id, schedule_id, current_user)


# ---------------------------------------------------------------------------
# Disponibilidade e agenda do dia
# ---------------------------------------------------------------------------
@router.get(
    "/{professional_id}/available-slots",
    response_model=AvailabilityResponse,
    summary="Horarios livres do profissional em uma data",
)
def available_slots(
    professional_id: int,
    day: date = Query(..., alias="date", description="Data no formato YYYY-MM-DD"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AvailabilityResponse:
    slots = ProfessionalService(db).build_slots(professional_id, day)
    return AvailabilityResponse(professional_id=professional_id, date=day, slots=slots)


@router.get(
    "/{professional_id}/agenda",
    response_model=DailyAgendaResponse,
    summary="Agenda do dia do profissional",
)
def daily_agenda(
    professional_id: int,
    day: date = Query(..., alias="date", description="Data no formato YYYY-MM-DD"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DailyAgendaResponse:
    data = AppointmentService(db).daily_agenda(professional_id, day, current_user)
    return DailyAgendaResponse.model_validate(data)
