"""Reporting and indicator endpoints."""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.database import get_db
from app.dependencies import require_roles
from app.models.user import User
from app.schemas.report import (
    AppointmentsByPeriodItem,
    AppointmentsByProfessionalItem,
    AppointmentsBySpecialtyItem,
    AppointmentsByStatusItem,
    NoShowRateItem,
    RevenueByPaymentMethodItem,
    RevenueByPeriodItem,
    TopPatientItem,
)
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Relatórios"])

REPORT_ROLES = (UserRole.ADMIN, UserRole.RECEPCIONISTA)


@router.get("/appointments-by-period", response_model=list[AppointmentsByPeriodItem])
def appointments_by_period(
    date_from: date = Query(...),
    date_to: date = Query(...),
    current_user: User = Depends(require_roles(*REPORT_ROLES)),
    db: Session = Depends(get_db),
):
    service = ReportService(db)
    return service.appointments_by_period(date_from, date_to)


@router.get("/appointments-by-professional", response_model=list[AppointmentsByProfessionalItem])
def appointments_by_professional(
    date_from: date = Query(...),
    date_to: date = Query(...),
    current_user: User = Depends(require_roles(*REPORT_ROLES)),
    db: Session = Depends(get_db),
):
    service = ReportService(db)
    return service.appointments_by_professional(date_from, date_to)


@router.get("/appointments-by-specialty", response_model=list[AppointmentsBySpecialtyItem])
def appointments_by_specialty(
    date_from: date = Query(...),
    date_to: date = Query(...),
    current_user: User = Depends(require_roles(*REPORT_ROLES)),
    db: Session = Depends(get_db),
):
    service = ReportService(db)
    return service.appointments_by_specialty(date_from, date_to)


@router.get("/appointments-by-status", response_model=list[AppointmentsByStatusItem])
def appointments_by_status(
    date_from: date = Query(...),
    date_to: date = Query(...),
    current_user: User = Depends(require_roles(*REPORT_ROLES)),
    db: Session = Depends(get_db),
):
    service = ReportService(db)
    return service.appointments_by_status(date_from, date_to)


@router.get("/revenue-by-period", response_model=list[RevenueByPeriodItem])
def revenue_by_period(
    date_from: date = Query(...),
    date_to: date = Query(...),
    current_user: User = Depends(require_roles(*REPORT_ROLES)),
    db: Session = Depends(get_db),
):
    service = ReportService(db)
    return service.revenue_by_period(date_from, date_to)


@router.get("/revenue-by-payment-method", response_model=list[RevenueByPaymentMethodItem])
def revenue_by_payment_method(
    date_from: date = Query(...),
    date_to: date = Query(...),
    current_user: User = Depends(require_roles(*REPORT_ROLES)),
    db: Session = Depends(get_db),
):
    service = ReportService(db)
    return service.revenue_by_payment_method(date_from, date_to)


@router.get("/no-show-rate", response_model=list[NoShowRateItem])
def no_show_rate(
    date_from: date = Query(...),
    date_to: date = Query(...),
    current_user: User = Depends(require_roles(*REPORT_ROLES)),
    db: Session = Depends(get_db),
):
    service = ReportService(db)
    return service.no_show_rate(date_from, date_to)


@router.get("/top-patients", response_model=list[TopPatientItem])
def top_patients(
    date_from: date = Query(...),
    date_to: date = Query(...),
    limit: int = Query(default=10, ge=1, le=100),
    current_user: User = Depends(require_roles(*REPORT_ROLES)),
    db: Session = Depends(get_db),
):
    service = ReportService(db)
    return service.top_patients(date_from, date_to, limit)
