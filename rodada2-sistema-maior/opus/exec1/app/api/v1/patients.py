"""Rotas de pacientes e convenios."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_admin, require_front_desk
from app.core.pagination import Page, PaginationParams
from app.db.session import get_db
from app.models.user import User
from app.schemas.medical_record import ClinicalHistoryResponse
from app.schemas.patient import (
    HealthInsuranceCreate,
    HealthInsuranceRead,
    HealthInsuranceUpdate,
    PatientCreate,
    PatientRead,
    PatientUpdate,
)
from app.services.medical_record_service import MedicalRecordService
from app.services.patient_service import HealthInsuranceService, PatientService

router = APIRouter(prefix="/patients", tags=["Pacientes"])
insurance_router = APIRouter(prefix="/insurances", tags=["Convenios"])


# ---------------------------------------------------------------------------
# Convenios
# ---------------------------------------------------------------------------
@insurance_router.post(
    "",
    response_model=HealthInsuranceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um convenio",
)
def create_insurance(
    payload: HealthInsuranceCreate,
    current_user: User = Depends(require_front_desk),
    db: Session = Depends(get_db),
) -> HealthInsuranceRead:
    return HealthInsuranceRead.model_validate(
        HealthInsuranceService(db).create(payload, current_user)
    )


@insurance_router.get("", response_model=Page[HealthInsuranceRead], summary="Lista convenios")
def list_insurances(
    pagination: PaginationParams = Depends(),
    query: str | None = Query(None, description="Busca pelo nome do convenio"),
    is_active: bool | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[HealthInsuranceRead]:
    items, total = HealthInsuranceService(db).search(pagination, query=query, is_active=is_active)
    return Page.create(
        [HealthInsuranceRead.model_validate(item) for item in items],
        total,
        pagination.page,
        pagination.size,
    )


@insurance_router.get(
    "/{insurance_id}", response_model=HealthInsuranceRead, summary="Detalha um convenio"
)
def get_insurance(
    insurance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HealthInsuranceRead:
    return HealthInsuranceRead.model_validate(HealthInsuranceService(db).get(insurance_id))


@insurance_router.patch(
    "/{insurance_id}", response_model=HealthInsuranceRead, summary="Atualiza um convenio"
)
def update_insurance(
    insurance_id: int,
    payload: HealthInsuranceUpdate,
    current_user: User = Depends(require_front_desk),
    db: Session = Depends(get_db),
) -> HealthInsuranceRead:
    return HealthInsuranceRead.model_validate(
        HealthInsuranceService(db).update(insurance_id, payload, current_user)
    )


# ---------------------------------------------------------------------------
# Pacientes
# ---------------------------------------------------------------------------
@router.post(
    "",
    response_model=PatientRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um paciente",
    description="Disponivel para administradores e recepcionistas.",
)
def create_patient(
    payload: PatientCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PatientRead:
    return PatientRead.model_validate(PatientService(db).create(payload, current_user))


@router.get(
    "",
    response_model=Page[PatientRead],
    summary="Busca pacientes por nome, CPF ou convenio",
    description=(
        "Equipe da clinica enxerga todos os pacientes. "
        "Um usuario com perfil `patient` recebe apenas o proprio cadastro."
    ),
)
def list_patients(
    pagination: PaginationParams = Depends(),
    query: str | None = Query(None, description="Nome ou CPF do paciente"),
    cpf: str | None = Query(None, description="Filtra por CPF (com ou sem mascara)"),
    insurance_id: int | None = Query(None),
    insurance: str | None = Query(None, description="Nome do convenio"),
    city: str | None = Query(None),
    is_active: bool | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[PatientRead]:
    items, total = PatientService(db).search(
        pagination,
        current_user,
        query=query,
        cpf=cpf,
        insurance_id=insurance_id,
        insurance_name=insurance,
        city=city,
        is_active=is_active,
    )
    return Page.create(
        [PatientRead.model_validate(item) for item in items],
        total,
        pagination.page,
        pagination.size,
    )


@router.get("/me", response_model=PatientRead, summary="Cadastro do paciente autenticado")
def get_own_patient(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> PatientRead:
    return PatientRead.model_validate(PatientService(db).resolve_own_patient(current_user))


@router.get("/{patient_id}", response_model=PatientRead, summary="Detalha um paciente")
def get_patient(
    patient_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PatientRead:
    return PatientRead.model_validate(PatientService(db).get(patient_id, current_user))


@router.patch("/{patient_id}", response_model=PatientRead, summary="Atualiza um paciente")
def update_patient(
    patient_id: int,
    payload: PatientUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PatientRead:
    return PatientRead.model_validate(
        PatientService(db).update(patient_id, payload, current_user)
    )


@router.delete(
    "/{patient_id}",
    response_model=PatientRead,
    summary="Exclusao logica do paciente (apenas administrador)",
)
def delete_patient(
    patient_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PatientRead:
    return PatientRead.model_validate(PatientService(db).deactivate(patient_id, current_user))


@router.get(
    "/{patient_id}/history",
    response_model=ClinicalHistoryResponse,
    summary="Historico clinico completo em ordem cronologica",
)
def clinical_history(
    patient_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClinicalHistoryResponse:
    data = MedicalRecordService(db).clinical_history(patient_id, current_user)
    return ClinicalHistoryResponse.model_validate(data)
