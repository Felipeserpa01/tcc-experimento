from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, get_current_user, require_roles
from app.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.medical_record import (
    ExamCreate,
    ExamRead,
    ExamResultUpdate,
    MedicalRecordCreate,
    MedicalRecordRead,
    PrescriptionCreate,
    PrescriptionRead,
)
from app.services.medical_record_service import MedicalRecordService

router = APIRouter(tags=["Prontuário"])


@router.post(
    "/appointments/{appointment_id}/medical-record",
    response_model=MedicalRecordRead,
    status_code=status.HTTP_201_CREATED,
)
def create_medical_record(
    appointment_id: int,
    payload: MedicalRecordCreate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.DOCTOR)),
    db: Session = Depends(get_db),
):
    service = MedicalRecordService(db)
    return service.create_record(appointment_id, payload, current_user, ip_address=get_client_ip(request))


@router.get("/medical-records/{record_id}", response_model=MedicalRecordRead)
def get_medical_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = MedicalRecordService(db)
    return service.get_record(record_id, current_user)


@router.post(
    "/medical-records/{record_id}/prescriptions",
    response_model=PrescriptionRead,
    status_code=status.HTTP_201_CREATED,
)
def add_prescription(
    record_id: int,
    payload: PrescriptionCreate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.DOCTOR)),
    db: Session = Depends(get_db),
):
    service = MedicalRecordService(db)
    return service.add_prescription(record_id, payload, current_user, ip_address=get_client_ip(request))


@router.post(
    "/medical-records/{record_id}/exams", response_model=ExamRead, status_code=status.HTTP_201_CREATED
)
def add_exam(
    record_id: int,
    payload: ExamCreate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.DOCTOR)),
    db: Session = Depends(get_db),
):
    service = MedicalRecordService(db)
    return service.add_exam(record_id, payload, current_user, ip_address=get_client_ip(request))


@router.patch("/exams/{exam_id}/result", response_model=ExamRead)
def attach_exam_result(
    exam_id: int,
    payload: ExamResultUpdate,
    request: Request,
    current_user: User = Depends(require_roles(UserRole.DOCTOR)),
    db: Session = Depends(get_db),
):
    service = MedicalRecordService(db)
    return service.attach_exam_result(exam_id, payload.result, current_user, ip_address=get_client_ip(request))


@router.get("/patients/{patient_id}/history")
def get_patient_history(
    patient_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = MedicalRecordService(db)
    appointments = service.get_patient_history(patient_id, current_user)

    history = []
    for appt in appointments:
        record = None
        if appt.medical_record:
            record = MedicalRecordRead.model_validate(appt.medical_record)
        history.append(
            {
                "appointment_id": appt.id,
                "scheduled_at": appt.scheduled_at,
                "doctor_name": appt.doctor.full_name,
                "status": appt.status.value,
                "medical_record": record,
            }
        )
    return history
