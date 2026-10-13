from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.report import (
    AppointmentReportEntry,
    BillingReportEntry,
    NoShowRateEntry,
    StatusCount,
    TopPatientEntry,
)
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Relatórios"])


@router.get("/appointments", response_model=list[AppointmentReportEntry])
def appointments_report(
    start: date | None = Query(None),
    end: date | None = Query(None),
    doctor_id: int | None = Query(None),
    specialty: str | None = Query(None),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    service = ReportService(db)
    return service.appointments_report(start, end, doctor_id, specialty)


@router.get("/appointments/status-summary", response_model=list[StatusCount])
def status_summary(
    start: date | None = Query(None),
    end: date | None = Query(None),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    service = ReportService(db)
    return service.status_summary(start, end)


@router.get("/billing", response_model=BillingReportEntry)
def billing_report(
    start: date = Query(...),
    end: date = Query(...),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    service = ReportService(db)
    return service.billing_report(start, end)


@router.get("/no-show-rate", response_model=list[NoShowRateEntry])
def no_show_rate(
    doctor_id: int | None = Query(None),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    service = ReportService(db)
    return service.no_show_rate(doctor_id)


@router.get("/top-patients", response_model=list[TopPatientEntry])
def top_patients(
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    service = ReportService(db)
    return service.top_patients(limit)
