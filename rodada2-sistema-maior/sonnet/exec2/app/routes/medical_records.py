"""Medical record, prescription, exam and clinical history endpoints."""
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.database import get_db
from app.dependencies import get_client_ip, get_current_user, require_roles
from app.models.user import User
from app.schemas.medical_record import (
    ExamCreate,
    ExamOut,
    ExamResultUpdate,
    MedicalRecordCreate,
    MedicalRecordOut,
    PrescriptionCreate,
    PrescriptionOut,
)
from app.services.medical_record_service import MedicalRecordService

router = APIRouter(tags=["Prontuário, Prescrições e Exames"])

CLINICAL_HISTORY_ROLES = (UserRole.ADMIN, UserRole.MEDICO, UserRole.ENFERMEIRO, UserRole.PACIENTE)


@router.post(
    "/appointments/{appointment_id}/medical-record",
    response_model=MedicalRecordOut,
    status_code=status.HTTP_201_CREATED,
)
def create_medical_record(
    appointment_id: int,
    payload: MedicalRecordCreate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MEDICO)),
    db: Session = Depends(get_db),
):
    service = MedicalRecordService(db)
    return service.create_medical_record(
        appointment_id, payload, current_user, ip_address=get_client_ip(request)
    )


@router.get("/appointments/{appointment_id}/medical-record", response_model=MedicalRecordOut)
def get_medical_record(
    appointment_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    service = MedicalRecordService(db)
    return service.get_medical_record(appointment_id, current_user)


@router.post(
    "/appointments/{appointment_id}/prescriptions",
    response_model=PrescriptionOut,
    status_code=status.HTTP_201_CREATED,
)
def add_prescription(
    appointment_id: int,
    payload: PrescriptionCreate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MEDICO)),
    db: Session = Depends(get_db),
):
    service = MedicalRecordService(db)
    return service.add_prescription(
        appointment_id, payload, current_user, ip_address=get_client_ip(request)
    )


@router.get("/appointments/{appointment_id}/prescriptions", response_model=list[PrescriptionOut])
def get_prescriptions(
    appointment_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    service = MedicalRecordService(db)
    return service.get_prescriptions(appointment_id, current_user)


@router.post(
    "/appointments/{appointment_id}/exams", response_model=ExamOut, status_code=status.HTTP_201_CREATED
)
def add_exam(
    appointment_id: int,
    payload: ExamCreate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MEDICO)),
    db: Session = Depends(get_db),
):
    service = MedicalRecordService(db)
    return service.add_exam(appointment_id, payload, current_user, ip_address=get_client_ip(request))


@router.get("/appointments/{appointment_id}/exams", response_model=list[ExamOut])
def get_exams(
    appointment_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    service = MedicalRecordService(db)
    return service.get_exams(appointment_id, current_user)


@router.patch("/exams/{exam_id}/result", response_model=ExamOut)
def attach_exam_result(
    exam_id: int,
    payload: ExamResultUpdate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.MEDICO)),
    db: Session = Depends(get_db),
):
    service = MedicalRecordService(db)
    return service.attach_exam_result(
        exam_id, payload.resultado, current_user, ip_address=get_client_ip(request)
    )


@router.get("/patients/{patient_id}/history", response_model=list[dict])
def get_patient_history(
    patient_id: int,
    current_user: User = Depends(require_roles(*CLINICAL_HISTORY_ROLES)),
    db: Session = Depends(get_db),
):
    service = MedicalRecordService(db)
    return service.get_patient_history(patient_id, current_user)
