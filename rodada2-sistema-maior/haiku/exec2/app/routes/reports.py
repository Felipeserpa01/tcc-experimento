from fastapi import APIRouter, Depends, Query
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models import UserRole
from app.services.reports_service import ReportsService

router = APIRouter()

@router.get("/appointments/period", response_model=list)
def get_appointments_by_period(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user = Depends(require_role(UserRole.ADMIN, UserRole.RECEPTIONIST)),
    db: Session = Depends(get_db)
):
    service = ReportsService(db)
    return service.get_appointments_by_period(start_date, end_date, skip, limit)

@router.get("/appointments/doctor/{professional_id}", response_model=list)
def get_appointments_by_doctor(
    professional_id: int,
    start_date: datetime = Query(None),
    end_date: datetime = Query(None),
    current_user = Depends(require_role(UserRole.ADMIN, UserRole.RECEPTIONIST, UserRole.DOCTOR)),
    db: Session = Depends(get_db)
):
    service = ReportsService(db)
    return service.get_appointments_by_doctor(professional_id, start_date, end_date)

@router.get("/appointments/specialization/{specialization}", response_model=list)
def get_appointments_by_specialization(
    specialization: str,
    start_date: datetime = Query(None),
    end_date: datetime = Query(None),
    current_user = Depends(require_role(UserRole.ADMIN, UserRole.RECEPTIONIST)),
    db: Session = Depends(get_db)
):
    service = ReportsService(db)
    return service.get_appointments_by_specialization(specialization, start_date, end_date)

@router.get("/appointments/count-by-status", response_model=dict)
def get_appointments_count_by_status(
    current_user = Depends(require_role(UserRole.ADMIN, UserRole.RECEPTIONIST)),
    db: Session = Depends(get_db)
):
    service = ReportsService(db)
    return service.get_appointments_count_by_status()

@router.get("/revenue/period", response_model=dict)
def get_revenue_by_period(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    current_user = Depends(require_role(UserRole.ADMIN, UserRole.RECEPTIONIST)),
    db: Session = Depends(get_db)
):
    service = ReportsService(db)
    return service.get_revenue_by_period(start_date, end_date)

@router.get("/revenue/payment-method", response_model=dict)
def get_revenue_by_payment_method(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    current_user = Depends(require_role(UserRole.ADMIN, UserRole.RECEPTIONIST)),
    db: Session = Depends(get_db)
):
    service = ReportsService(db)
    return service.get_revenue_by_payment_method(start_date, end_date)

@router.get("/no-show-rate", response_model=list)
def get_no_show_rate(
    professional_id: int = Query(None),
    current_user = Depends(require_role(UserRole.ADMIN, UserRole.RECEPTIONIST)),
    db: Session = Depends(get_db)
):
    service = ReportsService(db)
    return service.get_no_show_rate_by_doctor(professional_id)

@router.get("/most-attended-patients", response_model=list)
def get_most_attended_patients(
    limit: int = Query(10, ge=1, le=100),
    current_user = Depends(require_role(UserRole.ADMIN, UserRole.RECEPTIONIST)),
    db: Session = Depends(get_db)
):
    service = ReportsService(db)
    return service.get_most_attended_patients(limit)

@router.get("/audit-logs", response_model=list)
def get_audit_logs(
    user_id: int = Query(None),
    action: str = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    service = ReportsService(db)
    return service.get_audit_logs(user_id, action, skip, limit)
