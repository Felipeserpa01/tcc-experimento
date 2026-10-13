from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models import UserRole
from app.schemas import MedicalRecordCreate, MedicalRecordResponse, PrescriptionCreate, PrescriptionResponse, ExamCreate, ExamResponse, ExamUpdate
from app.services.medical_record_service import MedicalRecordService

router = APIRouter()

@router.post("/", response_model=MedicalRecordResponse)
def create_medical_record(
    record_data: MedicalRecordCreate,
    current_user = Depends(require_role(UserRole.DOCTOR)),
    db: Session = Depends(get_db)
):
    service = MedicalRecordService(db)
    return service.create_record(record_data, current_user.id)

@router.get("/{record_id}", response_model=MedicalRecordResponse)
def get_medical_record(
    record_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = MedicalRecordService(db)
    return service.get_record(record_id, current_user.id, current_user.role.value)

@router.get("/patient/{patient_id}/history", response_model=list)
def get_patient_history(
    patient_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = MedicalRecordService(db)
    return service.get_patient_history(patient_id, skip, limit)

@router.post("/{record_id}/prescriptions", response_model=PrescriptionResponse)
def add_prescription(
    record_id: int,
    prescription_data: PrescriptionCreate,
    current_user = Depends(require_role(UserRole.DOCTOR)),
    db: Session = Depends(get_db)
):
    if prescription_data.medical_record_id != record_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Record ID mismatch")

    service = MedicalRecordService(db)
    return service.add_prescription(prescription_data, current_user.id)

@router.get("/{record_id}/prescriptions", response_model=list)
def get_prescriptions(
    record_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = MedicalRecordService(db)
    service.get_record(record_id, current_user.id, current_user.role.value)
    return service.get_prescriptions(record_id)

@router.post("/{record_id}/exams", response_model=ExamResponse)
def add_exam(
    record_id: int,
    exam_data: ExamCreate,
    current_user = Depends(require_role(UserRole.DOCTOR)),
    db: Session = Depends(get_db)
):
    if exam_data.medical_record_id != record_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Record ID mismatch")

    service = MedicalRecordService(db)
    return service.add_exam(exam_data, current_user.id)

@router.put("/exams/{exam_id}/result", response_model=ExamResponse)
def update_exam_result(
    exam_id: int,
    exam_update: ExamUpdate,
    current_user = Depends(require_role(UserRole.DOCTOR)),
    db: Session = Depends(get_db)
):
    service = MedicalRecordService(db)
    return service.update_exam_result(exam_id, exam_update, current_user.id)

@router.get("/{record_id}/exams", response_model=list)
def get_exams(
    record_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = MedicalRecordService(db)
    service.get_record(record_id, current_user.id, current_user.role.value)
    return service.get_exams(record_id)
