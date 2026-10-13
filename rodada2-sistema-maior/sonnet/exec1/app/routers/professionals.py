from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, get_current_user, require_roles
from app.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.common import Page
from app.schemas.professional import (
    AvailabilityCreate,
    AvailabilityRead,
    ProfessionalCreate,
    ProfessionalRead,
    ProfessionalUpdate,
)
from app.services.professional_service import ProfessionalService
from app.utils.pagination import PageParams

router = APIRouter(prefix="/professionals", tags=["Profissionais"])


@router.post("", response_model=ProfessionalRead, status_code=status.HTTP_201_CREATED)
def create_professional(
    payload: ProfessionalCreate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    service = ProfessionalService(db)
    return service.create_professional(payload, current_user.id, ip_address=get_client_ip(request))


@router.get("", response_model=Page[ProfessionalRead])
def search_professionals(
    specialty: str | None = Query(None),
    professional_type: str | None = Query(None),
    params: PageParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ProfessionalService(db)
    items, total = service.search_professionals(
        specialty, professional_type, params.offset, params.page_size
    )
    return Page(total=total, page=params.page, page_size=params.page_size, items=items)


@router.get("/{professional_id}", response_model=ProfessionalRead)
def get_professional(
    professional_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ProfessionalService(db)
    return service.get_professional(professional_id)


@router.patch("/{professional_id}", response_model=ProfessionalRead)
def update_professional(
    professional_id: int,
    payload: ProfessionalUpdate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    service = ProfessionalService(db)
    return service.update_professional(
        professional_id, payload, current_user.id, ip_address=get_client_ip(request)
    )


@router.delete("/{professional_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_professional(
    professional_id: int,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    service = ProfessionalService(db)
    service.delete_professional(professional_id, current_user.id, ip_address=get_client_ip(request))


@router.post(
    "/{professional_id}/availability",
    response_model=AvailabilityRead,
    status_code=status.HTTP_201_CREATED,
)
def add_availability(
    professional_id: int,
    payload: AvailabilityCreate,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DOCTOR, UserRole.NURSE)),
    db: Session = Depends(get_db),
):
    service = ProfessionalService(db)
    return service.add_availability(professional_id, payload, current_user.id)


@router.get("/{professional_id}/availability", response_model=list[AvailabilityRead])
def list_availability(
    professional_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = ProfessionalService(db)
    return service.get_availabilities(professional_id)
