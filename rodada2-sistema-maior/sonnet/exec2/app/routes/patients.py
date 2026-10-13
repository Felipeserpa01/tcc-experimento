"""Patient management endpoints."""
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.database import get_db
from app.dependencies import get_client_ip, get_current_user, require_roles
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.patient import PatientCreate, PatientOut, PatientUpdate
from app.services.patient_service import PatientService

router = APIRouter(prefix="/patients", tags=["Pacientes"])

REGISTRATION_ROLES = (UserRole.ADMIN, UserRole.RECEPCIONISTA)
UPDATE_ROLES = (UserRole.ADMIN, UserRole.RECEPCIONISTA, UserRole.PACIENTE)


@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    request: Request,
    current_user: User = Depends(require_roles(*REGISTRATION_ROLES)),
    db: Session = Depends(get_db),
):
    service = PatientService(db)
    return service.create(payload, current_user, ip_address=get_client_ip(request))


@router.get("", response_model=PaginatedResponse[PatientOut])
def search_patients(
    nome: str | None = None,
    cpf: str | None = None,
    convenio: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str | None = None,
    sort_order: Literal["asc", "desc"] = "asc",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = PatientService(db)
    items, total = service.search(current_user, nome, cpf, convenio, page, page_size, sort_by, sort_order)
    return PaginatedResponse.build(items, total, page, page_size)


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(
    patient_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    service = PatientService(db)
    return service.get(patient_id, current_user)


@router.put("/{patient_id}", response_model=PatientOut)
def update_patient(
    patient_id: int,
    payload: PatientUpdate,
    request: Request,
    current_user: User = Depends(require_roles(*UPDATE_ROLES)),
    db: Session = Depends(get_db),
):
    service = PatientService(db)
    return service.update(patient_id, payload, current_user, ip_address=get_client_ip(request))


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(
    patient_id: int,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    service = PatientService(db)
    service.delete(patient_id, current_user, ip_address=get_client_ip(request))
