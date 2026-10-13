"""Appointment scheduling endpoints, including daily agenda and waitlist."""
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.enums import AppointmentStatus, UserRole
from app.database import get_db
from app.dependencies import get_client_ip, get_current_user, require_roles
from app.models.user import User
from app.schemas.appointment import (
    AppointmentCancel,
    AppointmentCreate,
    AppointmentOut,
    AppointmentReschedule,
    AppointmentStatusUpdate,
    WaitlistCreate,
    WaitlistOut,
)
from app.schemas.common import PaginatedResponse
from app.services.appointment_service import AppointmentService

router = APIRouter(tags=["Agendamento"])

BOOKING_ROLES = (UserRole.ADMIN, UserRole.RECEPCIONISTA, UserRole.PACIENTE)
PATIENT_ACTION_ROLES = (
    UserRole.ADMIN,
    UserRole.RECEPCIONISTA,
    UserRole.MEDICO,
    UserRole.ENFERMEIRO,
    UserRole.PACIENTE,
)
CLINICAL_STAFF_ROLES = (UserRole.ADMIN, UserRole.RECEPCIONISTA, UserRole.MEDICO, UserRole.ENFERMEIRO)


@router.post("/appointments", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
def schedule_appointment(
    payload: AppointmentCreate,
    request: Request,
    current_user: User = Depends(require_roles(*BOOKING_ROLES)),
    db: Session = Depends(get_db),
):
    service = AppointmentService(db)
    return service.schedule(payload, current_user, ip_address=get_client_ip(request))


@router.get("/appointments", response_model=PaginatedResponse[AppointmentOut])
def search_appointments(
    patient_id: int | None = None,
    professional_id: int | None = None,
    status_filter: AppointmentStatus | None = Query(default=None, alias="status"),
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str | None = None,
    sort_order: Literal["asc", "desc"] = "asc",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AppointmentService(db)
    items, total = service.search(
        current_user,
        patient_id,
        professional_id,
        status_filter,
        date_from,
        date_to,
        page,
        page_size,
        sort_by,
        sort_order,
    )
    return PaginatedResponse.build(items, total, page, page_size)


@router.get("/appointments/{appointment_id}", response_model=AppointmentOut)
def get_appointment(
    appointment_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    service = AppointmentService(db)
    return service.get(appointment_id, current_user)


@router.post("/appointments/{appointment_id}/confirm", response_model=AppointmentOut)
def confirm_appointment(
    appointment_id: int,
    request: Request,
    current_user: User = Depends(require_roles(*PATIENT_ACTION_ROLES)),
    db: Session = Depends(get_db),
):
    service = AppointmentService(db)
    return service.confirm(appointment_id, current_user, ip_address=get_client_ip(request))


@router.post("/appointments/{appointment_id}/cancel", response_model=AppointmentOut)
def cancel_appointment(
    appointment_id: int,
    payload: AppointmentCancel,
    request: Request,
    current_user: User = Depends(require_roles(*PATIENT_ACTION_ROLES)),
    db: Session = Depends(get_db),
):
    service = AppointmentService(db)
    return service.cancel(appointment_id, payload.motivo, current_user, ip_address=get_client_ip(request))


@router.put("/appointments/{appointment_id}/reschedule", response_model=AppointmentOut)
def reschedule_appointment(
    appointment_id: int,
    payload: AppointmentReschedule,
    request: Request,
    current_user: User = Depends(require_roles(*PATIENT_ACTION_ROLES)),
    db: Session = Depends(get_db),
):
    service = AppointmentService(db)
    return service.reschedule(
        appointment_id, payload.data_hora, current_user, ip_address=get_client_ip(request)
    )


@router.patch("/appointments/{appointment_id}/status", response_model=AppointmentOut)
def update_appointment_status(
    appointment_id: int,
    payload: AppointmentStatusUpdate,
    request: Request,
    current_user: User = Depends(require_roles(*CLINICAL_STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    service = AppointmentService(db)
    return service.update_status(
        appointment_id, payload.status, current_user, ip_address=get_client_ip(request)
    )


@router.get("/professionals/{professional_id}/agenda", response_model=list[AppointmentOut])
def get_daily_agenda(
    professional_id: int,
    day: date = Query(description="Data da agenda no formato YYYY-MM-DD"),
    current_user: User = Depends(require_roles(*CLINICAL_STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    service = AppointmentService(db)
    return service.get_daily_agenda(professional_id, day)


@router.post("/waitlist", response_model=WaitlistOut, status_code=status.HTTP_201_CREATED)
def join_waitlist(
    payload: WaitlistCreate,
    request: Request,
    current_user: User = Depends(require_roles(*BOOKING_ROLES)),
    db: Session = Depends(get_db),
):
    service = AppointmentService(db)
    return service.join_waitlist(payload, current_user, ip_address=get_client_ip(request))
