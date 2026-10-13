from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, get_current_user, require_roles
from app.core.permissions import STAFF_ROLES
from app.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.common import Page
from app.schemas.patient import PatientCreate, PatientRead, PatientUpdate
from app.services.patient_service import PatientService
from app.utils.pagination import PageParams

router = APIRouter(prefix="/patients", tags=["Pacientes"])


@router.post("", response_model=PatientRead, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    request: Request,
    current_user: User = Depends(require_roles(*STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    service = PatientService(db)
    return service.create_patient(payload, current_user, ip_address=get_client_ip(request))


@router.get("", response_model=Page[PatientRead])
def search_patients(
    name: str | None = Query(None),
    cpf: str | None = Query(None),
    insurance: str | None = Query(None),
    order_by: Literal["full_name", "cpf", "insurance", "created_at"] = Query("full_name"),
    descending: bool = Query(False),
    params: PageParams = Depends(),
    current_user: User = Depends(require_roles(*STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    service = PatientService(db)
    items, total = service.search_patients(
        name, cpf, insurance, order_by, descending, params.offset, params.page_size
    )
    return Page(total=total, page=params.page, page_size=params.page_size, items=items)


@router.get("/me", response_model=PatientRead)
def get_own_profile(
    current_user: User = Depends(require_roles(UserRole.PATIENT)),
    db: Session = Depends(get_db),
):
    service = PatientService(db)
    return service.get_own_patient_profile(current_user)


@router.get("/{patient_id}", response_model=PatientRead)
def get_patient(
    patient_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = PatientService(db)
    return service.get_patient(patient_id, current_user)


@router.patch("/{patient_id}", response_model=PatientRead)
def update_patient(
    patient_id: int,
    payload: PatientUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = PatientService(db)
    return service.update_patient(patient_id, payload, current_user, ip_address=get_client_ip(request))


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(
    patient_id: int,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    service = PatientService(db)
    service.delete_patient(patient_id, current_user, ip_address=get_client_ip(request))
