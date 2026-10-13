from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import ERROR_RESPONSES, Pagination, get_clinical_service, get_patient_service, require, sorting
from app.api.presenters import build_clinical_history
from app.core.pagination import SortParams
from app.core.permissions import Permission
from app.models.user import User
from app.schemas.clinical import ClinicalHistoryOut
from app.schemas.common import Page
from app.schemas.patient import PatientCreate, PatientOut, PatientUpdate
from app.services.clinical_service import ClinicalService
from app.services.patient_service import PatientService

router = APIRouter(prefix="/patients", tags=["Pacientes"], responses=ERROR_RESPONSES)

Patients = Annotated[PatientService, Depends(get_patient_service)]
PatientSort = Annotated[
    SortParams, Depends(sorting("full_name", "birth_date", "created_at", "cpf", default="full_name"))
]


@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED, summary="Cadastrar paciente")
def create_patient(
    data: PatientCreate,
    actor: Annotated[User, Depends(require(Permission.PATIENTS_CREATE))],
    service: Patients,
) -> object:
    return service.create(actor, data)


@router.get("", response_model=Page[PatientOut], summary="Buscar pacientes (nome, CPF ou convênio)")
def search_patients(
    actor: Annotated[User, Depends(require(Permission.PATIENTS_READ))],
    service: Patients,
    page: Pagination,
    sort: PatientSort,
    q: Annotated[str | None, Query(min_length=2, max_length=100, description="Nome ou CPF (parcial)")] = None,
    name: Annotated[str | None, Query(min_length=2, max_length=150)] = None,
    cpf: Annotated[str | None, Query(min_length=3, max_length=14, description="CPF completo ou prefixo")] = None,
    insurance_id: Annotated[int | None, Query(gt=0)] = None,
    insurance_name: Annotated[str | None, Query(min_length=2, max_length=100)] = None,
    is_active: bool | None = True,
) -> object:
    return service.search(
        actor,
        page,
        sort,
        query=q,
        name=name,
        cpf=cpf,
        insurance_id=insurance_id,
        insurance_name=insurance_name,
        is_active=is_active,
    )


@router.get("/me", response_model=PatientOut, summary="Ficha do paciente autenticado")
def my_patient_record(actor: Annotated[User, Depends(require(Permission.PATIENTS_READ))], service: Patients) -> object:
    return service.get_own(actor)


@router.get("/{patient_id}", response_model=PatientOut, summary="Detalhar paciente")
def get_patient(
    patient_id: int, actor: Annotated[User, Depends(require(Permission.PATIENTS_READ))], service: Patients
) -> object:
    return service.get(actor, patient_id)


@router.patch(
    "/{patient_id}",
    response_model=PatientOut,
    summary="Atualizar paciente",
    description=(
        "Recepção/administração alteram qualquer campo; médicos e enfermeiros apenas alergias e observações; "
        "o paciente apenas os próprios dados de contato (telefone, e-mail e endereço)."
    ),
)
def update_patient(
    patient_id: int,
    data: PatientUpdate,
    actor: Annotated[User, Depends(require(Permission.PATIENTS_UPDATE))],
    service: Patients,
) -> object:
    return service.update(actor, patient_id, data)


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Desativar paciente")
def deactivate_patient(
    patient_id: int, actor: Annotated[User, Depends(require(Permission.PATIENTS_DELETE))], service: Patients
) -> None:
    """Exclusão lógica: o histórico clínico e financeiro é preservado."""
    service.deactivate(actor, patient_id)


@router.get(
    "/{patient_id}/clinical-history",
    response_model=ClinicalHistoryOut,
    summary="Histórico clínico completo (ordem cronológica)",
)
def clinical_history(
    patient_id: int,
    actor: Annotated[User, Depends(require(Permission.CLINICAL_READ))],
    service: Annotated[ClinicalService, Depends(get_clinical_service)],
    date_from: date | None = None,
    date_to: date | None = None,
) -> ClinicalHistoryOut:
    patient, appointments = service.clinical_history(actor, patient_id, date_from, date_to)
    return build_clinical_history(patient, appointments)
