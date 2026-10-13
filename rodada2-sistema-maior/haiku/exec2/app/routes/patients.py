from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models import UserRole, Patient, User
from app.schemas import PatientCreate, PatientUpdate, PatientResponse, UserCreate
from app.services.patient_service import PatientService

router = APIRouter()

@router.post("/", response_model=PatientResponse)
def create_patient(
    patient_data: PatientCreate,
    current_user = Depends(require_role(UserRole.ADMIN, UserRole.RECEPTIONIST)),
    db: Session = Depends(get_db)
):
    service = PatientService(db)
    return service.create_patient(patient_data)

@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = PatientService(db)
    return service.get_patient(patient_id, current_user.id, current_user.role.value)

@router.put("/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: int,
    patient_data: PatientUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = PatientService(db)
    return service.update_patient(patient_id, patient_data, current_user.id, current_user.role.value)

@router.get("/", response_model=list)
def list_patients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    name: str = Query(None),
    cpf: str = Query(None),
    insurance_plan: str = Query(None),
    sort_by: str = Query("created_at"),
    current_user = Depends(require_role(UserRole.ADMIN, UserRole.RECEPTIONIST, UserRole.DOCTOR, UserRole.NURSE)),
    db: Session = Depends(get_db)
):
    service = PatientService(db)
    return service.list_patients(skip, limit, name, cpf, insurance_plan, sort_by)

@router.delete("/{patient_id}", response_model=dict)
def delete_patient(
    patient_id: int,
    current_user = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    service = PatientService(db)
    if service.delete_patient(patient_id):
        return {"message": "Patient deleted"}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
