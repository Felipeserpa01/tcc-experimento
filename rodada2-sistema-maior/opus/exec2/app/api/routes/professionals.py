from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import (
    ERROR_RESPONSES,
    Pagination,
    get_appointment_service,
    get_professional_service,
    require,
    sorting,
)
from app.core.pagination import SortParams
from app.core.permissions import Permission
from app.models.enums import ProfessionalType
from app.models.user import User
from app.schemas.appointment import AppointmentOut, DailyAgendaOut
from app.schemas.common import Page
from app.schemas.professional import (
    AvailabilityCreate,
    AvailabilityOut,
    AvailableSlotsOut,
    ProfessionalCreate,
    ProfessionalOut,
    ProfessionalSummary,
    ProfessionalUpdate,
    TimeSlot,
)
from app.services.appointment_service import AppointmentService
from app.services.professional_service import ProfessionalService

router = APIRouter(prefix="/professionals", tags=["Profissionais"], responses=ERROR_RESPONSES)

Professionals = Annotated[ProfessionalService, Depends(get_professional_service)]
Reader = Annotated[User, Depends(require(Permission.PROFESSIONALS_READ))]
Manager = Annotated[User, Depends(require(Permission.PROFESSIONALS_MANAGE))]
AvailabilityManager = Annotated[User, Depends(require(Permission.AVAILABILITY_MANAGE))]
ProfessionalSort = Annotated[SortParams, Depends(sorting("full_name", "specialty", "created_at", default="full_name"))]


@router.post("", response_model=ProfessionalOut, status_code=status.HTTP_201_CREATED, summary="Cadastrar profissional")
def create_professional(data: ProfessionalCreate, actor: Manager, service: Professionals) -> object:
    return service.create(actor, data)


@router.get("", response_model=Page[ProfessionalOut], summary="Listar/buscar profissionais (ex.: por especialidade)")
def list_professionals(
    _: Reader,
    service: Professionals,
    page: Pagination,
    sort: ProfessionalSort,
    name: Annotated[str | None, Query(min_length=2, max_length=150)] = None,
    specialty: Annotated[str | None, Query(min_length=2, max_length=100)] = None,
    professional_type: ProfessionalType | None = None,
    is_active: bool | None = True,
) -> object:
    return service.search(
        page, sort, name=name, specialty=specialty, professional_type=professional_type, is_active=is_active
    )


@router.get("/specialties", response_model=list[str], summary="Especialidades médicas disponíveis")
def list_specialties(_: Reader, service: Professionals) -> list[str]:
    return service.list_specialties()


@router.get("/{professional_id}", response_model=ProfessionalOut, summary="Detalhar profissional")
def get_professional(professional_id: int, _: Reader, service: Professionals) -> object:
    return service.get(professional_id)


@router.patch("/{professional_id}", response_model=ProfessionalOut, summary="Atualizar profissional")
def update_professional(
    professional_id: int, data: ProfessionalUpdate, actor: Manager, service: Professionals
) -> object:
    return service.update(actor, professional_id, data)


@router.delete("/{professional_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Desativar profissional")
def deactivate_professional(professional_id: int, actor: Manager, service: Professionals) -> None:
    service.deactivate(actor, professional_id)


# --------------------------------------------------------------------------- agenda de disponibilidade
@router.post(
    "/{professional_id}/availability",
    response_model=AvailabilityOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar faixa de disponibilidade",
)
def add_availability(
    professional_id: int, data: AvailabilityCreate, actor: AvailabilityManager, service: Professionals
) -> object:
    return service.add_availability(actor, professional_id, data)


@router.get(
    "/{professional_id}/availability", response_model=list[AvailabilityOut], summary="Agenda de disponibilidade"
)
def list_availability(professional_id: int, _: Reader, service: Professionals) -> object:
    return service.list_availability(professional_id)


@router.delete(
    "/{professional_id}/availability/{availability_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover faixa de disponibilidade",
)
def remove_availability(
    professional_id: int, availability_id: int, actor: AvailabilityManager, service: Professionals
) -> None:
    service.remove_availability(actor, professional_id, availability_id)


@router.get(
    "/{professional_id}/available-slots",
    response_model=AvailableSlotsOut,
    summary="Horários livres de um médico em uma data",
)
def available_slots(
    professional_id: int,
    _: Reader,
    service: Professionals,
    day: Annotated[date, Query(alias="date", description="Data (AAAA-MM-DD)")],
) -> AvailableSlotsOut:
    slots = service.available_slots(professional_id, day)
    return AvailableSlotsOut(
        professional_id=professional_id,
        date=day,
        slots=[TimeSlot(start_at=s.start_at, end_at=s.end_at) for s in slots],
    )


@router.get("/{professional_id}/agenda", response_model=DailyAgendaOut, summary="Agenda do dia de um médico")
def daily_agenda(
    professional_id: int,
    _: Annotated[User, Depends(require(Permission.AGENDA_READ))],
    service: Annotated[AppointmentService, Depends(get_appointment_service)],
    day: Annotated[date, Query(alias="date", description="Data (AAAA-MM-DD)")],
    include_cancelled: bool = False,
) -> DailyAgendaOut:
    professional, appointments = service.daily_agenda(professional_id, day, include_cancelled)
    return DailyAgendaOut(
        professional=ProfessionalSummary.model_validate(professional),
        date=day,
        total=len(appointments),
        appointments=[AppointmentOut.model_validate(a) for a in appointments],
    )
