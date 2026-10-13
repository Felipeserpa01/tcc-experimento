"""Professional (doctor/nurse) management endpoints."""
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.enums import ProfessionalType, UserRole
from app.database import get_db
from app.dependencies import get_client_ip, get_current_user, require_roles
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.professional import (
    AvailabilitySlotCreate,
    AvailabilitySlotOut,
    ProfessionalCreate,
    ProfessionalOut,
    ProfessionalUpdate,
)
from app.services.professional_service import ProfessionalService

router = APIRouter(prefix="/professionals", tags=["Profissionais"])


@router.post("", response_model=ProfessionalOut, status_code=status.HTTP_201_CREATED)
def create_professional(
    payload: ProfessionalCreate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    service = ProfessionalService(db)
    return service.create(payload, current_user, ip_address=get_client_ip(request))


@router.get("", response_model=PaginatedResponse[ProfessionalOut])
def search_professionals(
    especialidade: str | None = None,
    tipo: ProfessionalType | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str | None = None,
    sort_order: Literal["asc", "desc"] = "asc",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ProfessionalService(db)
    items, total = service.search(especialidade, tipo, page, page_size, sort_by, sort_order)
    return PaginatedResponse.build(items, total, page, page_size)


@router.get("/{professional_id}", response_model=ProfessionalOut)
def get_professional(
    professional_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    service = ProfessionalService(db)
    return service.get(professional_id)


@router.put("/{professional_id}", response_model=ProfessionalOut)
def update_professional(
    professional_id: int,
    payload: ProfessionalUpdate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    service = ProfessionalService(db)
    return service.update(professional_id, payload, current_user, ip_address=get_client_ip(request))


@router.delete("/{professional_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_professional(
    professional_id: int,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    service = ProfessionalService(db)
    service.delete(professional_id, current_user, ip_address=get_client_ip(request))


@router.post(
    "/{professional_id}/availability",
    response_model=AvailabilitySlotOut,
    status_code=status.HTTP_201_CREATED,
)
def add_availability_slot(
    professional_id: int,
    payload: AvailabilitySlotCreate,
    request: Request,
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MEDICO, UserRole.ENFERMEIRO)
    ),
    db: Session = Depends(get_db),
):
    service = ProfessionalService(db)
    return service.add_availability_slot(
        professional_id, payload, current_user, ip_address=get_client_ip(request)
    )


@router.delete("/{professional_id}/availability/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_availability_slot(
    professional_id: int,
    slot_id: int,
    request: Request,
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.MEDICO, UserRole.ENFERMEIRO)
    ),
    db: Session = Depends(get_db),
):
    service = ProfessionalService(db)
    service.remove_availability_slot(
        professional_id, slot_id, current_user, ip_address=get_client_ip(request)
    )
