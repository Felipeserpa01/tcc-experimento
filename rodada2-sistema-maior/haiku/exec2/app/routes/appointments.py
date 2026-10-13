from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models import UserRole
from app.schemas import AppointmentCreate, AppointmentUpdate, AppointmentResponse, WaitingListResponse
from app.services.appointment_service import AppointmentService

router = APIRouter()

@router.post("/", response_model=dict)
def create_appointment(
    appt_data: AppointmentCreate,
    current_user = Depends(require_role(UserRole.RECEPTIONIST, UserRole.PATIENT)),
    db: Session = Depends(get_db)
):
    service = AppointmentService(db)
    result = service.create_appointment(appt_data)

    if hasattr(result, 'position'):
        return {
            "message": "Added to waiting list",
            "position": result.position,
            "waiting_list_id": result.id
        }

    return {
        "id": result.id,
        "patient_id": result.patient_id,
        "professional_id": result.professional_id,
        "appointment_date": result.appointment_date,
        "status": result.status
    }

@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AppointmentService(db)
    return service.get_appointment(appointment_id)

@router.put("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: int,
    appt_data: AppointmentUpdate,
    current_user = Depends(require_role(UserRole.RECEPTIONIST, UserRole.DOCTOR, UserRole.NURSE)),
    db: Session = Depends(get_db)
):
    service = AppointmentService(db)
    return service.update_appointment(appointment_id, appt_data)

@router.post("/{appointment_id}/confirm", response_model=AppointmentResponse)
def confirm_appointment(
    appointment_id: int,
    current_user = Depends(require_role(UserRole.RECEPTIONIST, UserRole.DOCTOR)),
    db: Session = Depends(get_db)
):
    service = AppointmentService(db)
    return service.confirm_appointment(appointment_id)

@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
def cancel_appointment(
    appointment_id: int,
    reason: str = Query(...),
    current_user = Depends(require_role(UserRole.RECEPTIONIST, UserRole.DOCTOR)),
    db: Session = Depends(get_db)
):
    service = AppointmentService(db)
    return service.cancel_appointment(appointment_id, reason)

@router.post("/{appointment_id}/reschedule", response_model=AppointmentResponse)
def reschedule_appointment(
    appointment_id: int,
    new_date: datetime,
    current_user = Depends(require_role(UserRole.RECEPTIONIST)),
    db: Session = Depends(get_db)
):
    service = AppointmentService(db)
    return service.reschedule_appointment(appointment_id, new_date)

@router.get("/professional/{professional_id}/agenda", response_model=list)
def get_doctor_agenda(
    professional_id: int,
    date: datetime = Query(...),
    current_user = Depends(require_role(UserRole.DOCTOR, UserRole.RECEPTIONIST)),
    db: Session = Depends(get_db)
):
    service = AppointmentService(db)
    return service.get_doctor_agenda(professional_id, date)

@router.get("/patient/{patient_id}/appointments", response_model=list)
def list_patient_appointments(
    patient_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AppointmentService(db)
    return service.list_patient_appointments(patient_id, skip, limit)

@router.get("/status/{status}", response_model=list)
def list_appointments_by_status(
    status: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user = Depends(require_role(UserRole.ADMIN, UserRole.RECEPTIONIST)),
    db: Session = Depends(get_db)
):
    service = AppointmentService(db)
    return service.list_appointments_by_status(status, skip, limit)
