from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import (
    ERROR_RESPONSES,
    Pagination,
    get_appointment_service,
    get_clinical_service,
    require,
    sorting,
)
from app.core.pagination import SortOrder, SortParams
from app.core.permissions import Permission
from app.models.enums import AppointmentStatus
from app.models.user import User
from app.schemas.appointment import AppointmentCancel, AppointmentCreate, AppointmentOut, AppointmentReschedule
from app.schemas.clinical import (
    ExamOut,
    ExamRequestCreate,
    MedicalRecordCreate,
    MedicalRecordOut,
    MedicalRecordUpdate,
    PrescriptionCreate,
    PrescriptionOut,
)
from app.schemas.common import Page
from app.services.appointment_service import AppointmentService
from app.services.clinical_service import ClinicalService

router = APIRouter(prefix="/appointments", tags=["Consultas"], responses=ERROR_RESPONSES)

Appointments = Annotated[AppointmentService, Depends(get_appointment_service)]
Clinical = Annotated[ClinicalService, Depends(get_clinical_service)]
AppointmentSort = Annotated[
    SortParams, Depends(sorting("start_at", "created_at", "status", default="start_at", default_order=SortOrder.ASC))
]
Reader = Annotated[User, Depends(require(Permission.APPOINTMENTS_READ))]
Manager = Annotated[User, Depends(require(Permission.APPOINTMENTS_MANAGE))]
Attendant = Annotated[User, Depends(require(Permission.APPOINTMENTS_ATTEND))]
ClinicalReader = Annotated[User, Depends(require(Permission.CLINICAL_READ))]
ClinicalWriter = Annotated[User, Depends(require(Permission.CLINICAL_WRITE))]


@router.post("", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED, summary="Agendar consulta")
def schedule_appointment(
    data: AppointmentCreate,
    actor: Annotated[User, Depends(require(Permission.APPOINTMENTS_CREATE))],
    service: Appointments,
) -> object:
    """Valida disponibilidade do médico, conflitos de horário e datas passadas.

    Se o horário estiver ocupado, a resposta 409 indica que é possível entrar na lista de espera.
    """
    return service.schedule(actor, data)


@router.get("", response_model=Page[AppointmentOut], summary="Listar consultas (filtros e ordenação)")
def list_appointments(
    actor: Reader,
    service: Appointments,
    page: Pagination,
    sort: AppointmentSort,
    patient_id: Annotated[int | None, Query(gt=0)] = None,
    professional_id: Annotated[int | None, Query(gt=0)] = None,
    status_filter: Annotated[AppointmentStatus | None, Query(alias="status")] = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> object:
    return service.search(
        actor,
        page,
        sort,
        patient_id=patient_id,
        professional_id=professional_id,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/{appointment_id}", response_model=AppointmentOut, summary="Detalhar consulta")
def get_appointment(appointment_id: int, actor: Reader, service: Appointments) -> object:
    return service.get(actor, appointment_id)


@router.post("/{appointment_id}/confirm", response_model=AppointmentOut, summary="Confirmar consulta")
def confirm_appointment(appointment_id: int, actor: Manager, service: Appointments) -> object:
    return service.confirm(actor, appointment_id)


@router.post("/{appointment_id}/cancel", response_model=AppointmentOut, summary="Cancelar consulta (com motivo)")
def cancel_appointment(appointment_id: int, data: AppointmentCancel, actor: Manager, service: Appointments) -> object:
    """Ao cancelar, pacientes na lista de espera daquele horário são notificados."""
    return service.cancel(actor, appointment_id, data.reason)


@router.post("/{appointment_id}/reschedule", response_model=AppointmentOut, summary="Remarcar consulta")
def reschedule_appointment(
    appointment_id: int, data: AppointmentReschedule, actor: Manager, service: Appointments
) -> object:
    return service.reschedule(actor, appointment_id, data.start_at)


@router.post("/{appointment_id}/start", response_model=AppointmentOut, summary="Iniciar atendimento")
def start_appointment(appointment_id: int, actor: Attendant, service: Appointments) -> object:
    return service.start(actor, appointment_id)


@router.post("/{appointment_id}/complete", response_model=AppointmentOut, summary="Finalizar atendimento")
def complete_appointment(appointment_id: int, actor: Attendant, service: Appointments) -> object:
    return service.complete(actor, appointment_id)


@router.post("/{appointment_id}/no-show", response_model=AppointmentOut, summary="Registrar falta do paciente")
def mark_no_show(
    appointment_id: int,
    actor: Annotated[User, Depends(require(Permission.APPOINTMENTS_NO_SHOW))],
    service: Appointments,
) -> object:
    return service.mark_no_show(actor, appointment_id)


# --------------------------------------------------------------------------- prontuário
@router.post(
    "/{appointment_id}/medical-record",
    response_model=MedicalRecordOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Prontuário"],
    summary="Registrar prontuário (médico responsável)",
)
def create_medical_record(
    appointment_id: int, data: MedicalRecordCreate, actor: ClinicalWriter, service: Clinical
) -> object:
    return service.create_record(actor, appointment_id, data)


@router.get(
    "/{appointment_id}/medical-record",
    response_model=MedicalRecordOut,
    tags=["Prontuário"],
    summary="Consultar prontuário da consulta",
)
def get_medical_record(appointment_id: int, actor: ClinicalReader, service: Clinical) -> object:
    return service.get_record(actor, appointment_id)


@router.patch(
    "/{appointment_id}/medical-record",
    response_model=MedicalRecordOut,
    tags=["Prontuário"],
    summary="Atualizar prontuário (médico responsável)",
)
def update_medical_record(
    appointment_id: int, data: MedicalRecordUpdate, actor: ClinicalWriter, service: Clinical
) -> object:
    return service.update_record(actor, appointment_id, data)


# --------------------------------------------------------------------------- prescrições
@router.post(
    "/{appointment_id}/prescriptions",
    response_model=list[PrescriptionOut],
    status_code=status.HTTP_201_CREATED,
    tags=["Prontuário"],
    summary="Registrar prescrições (médico responsável)",
)
def create_prescriptions(
    appointment_id: int, data: PrescriptionCreate, actor: ClinicalWriter, service: Clinical
) -> object:
    return service.add_prescriptions(actor, appointment_id, data)


@router.get(
    "/{appointment_id}/prescriptions",
    response_model=list[PrescriptionOut],
    tags=["Prontuário"],
    summary="Prescrições da consulta",
)
def list_prescriptions(appointment_id: int, actor: ClinicalReader, service: Clinical) -> object:
    return service.list_prescriptions(actor, appointment_id)


# --------------------------------------------------------------------------- exames
@router.post(
    "/{appointment_id}/exams",
    response_model=list[ExamOut],
    status_code=status.HTTP_201_CREATED,
    tags=["Exames"],
    summary="Solicitar exames (médico responsável)",
)
def request_exams(appointment_id: int, data: ExamRequestCreate, actor: ClinicalWriter, service: Clinical) -> object:
    return service.request_exams(actor, appointment_id, data)


@router.get("/{appointment_id}/exams", response_model=list[ExamOut], tags=["Exames"], summary="Exames da consulta")
def list_exams(appointment_id: int, actor: ClinicalReader, service: Clinical) -> object:
    return service.list_exams(actor, appointment_id)
