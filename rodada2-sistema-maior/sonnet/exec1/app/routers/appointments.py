from datetime import date, datetime

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, get_current_user, require_roles
from app.core.permissions import SCHEDULING_ROLES
from app.database import get_db
from app.models.enums import AppointmentStatus, UserRole
from app.models.user import User
from app.schemas.appointment import (
    AppointmentCancel,
    AppointmentCreate,
    AppointmentRead,
    AppointmentReschedule,
    AppointmentStatusUpdate,
    WaitListCreate,
    WaitListRead,
)
from app.schemas.common import Page
from app.services.appointment_service import AppointmentService
from app.utils.pagination import PageParams

router = APIRouter(prefix="/appointments", tags=["Agendamento"])


@router.post("", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED)
def schedule_appointment(
    payload: AppointmentCreate,
    request: Request,
    current_user: User = Depends(
        require_roles(*SCHEDULING_ROLES, UserRole.PATIENT)
    ),
    db: Session = Depends(get_db),
):
    service = AppointmentService(db)
    return service.schedule(payload, current_user, ip_address=get_client_ip(request))


@router.get("", response_model=Page[AppointmentRead])
def search_appointments(
    patient_id: int | None = Query(None),
    doctor_id: int | None = Query(None),
    appointment_status: AppointmentStatus | None = Query(None),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    params: PageParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AppointmentService(db)
    items, total = service.search(
        patient_id, doctor_id, appointment_status, start, end, current_user, params.offset, params.page_size
    )
    return Page(total=total, page=params.page, page_size=params.page_size, items=items)


@router.get("/waitlist", response_model=Page[WaitListRead])
def list_waitlist(
    params: PageParams = Depends(),
    current_user: User = Depends(require_roles(*SCHEDULING_ROLES)),
    db: Session = Depends(get_db),
):
    service = AppointmentService(db)
    items, total = service.list_waitlist(params.offset, params.page_size)
    return Page(total=total, page=params.page, page_size=params.page_size, items=items)


@router.post("/waitlist", response_model=WaitListRead, status_code=status.HTTP_201_CREATED)
def join_waitlist(
    payload: WaitListCreate,
    current_user: User = Depends(require_roles(*SCHEDULING_ROLES, UserRole.PATIENT)),
    db: Session = Depends(get_db),
):
    service = AppointmentService(db)
    return service.join_waitlist(payload, current_user)


@router.get("/doctor/{doctor_id}/day", response_model=list[AppointmentRead])
def get_doctor_day_agenda(
    doctor_id: int,
    day: date = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AppointmentService(db)
    return service.get_doctor_day_agenda(doctor_id, day, current_user)


@router.get("/{appointment_id}", response_model=AppointmentRead)
def get_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AppointmentService(db)
    return service.get_appointment(appointment_id, current_user)


@router.patch("/{appointment_id}/confirm", response_model=AppointmentRead)
def confirm_appointment(
    appointment_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AppointmentService(db)
    return service.confirm(appointment_id, current_user, ip_address=get_client_ip(request))


@router.patch("/{appointment_id}/cancel", response_model=AppointmentRead)
def cancel_appointment(
    appointment_id: int,
    payload: AppointmentCancel,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AppointmentService(db)
    return service.cancel(appointment_id, payload.reason, current_user, ip_address=get_client_ip(request))


@router.patch("/{appointment_id}/reschedule", response_model=AppointmentRead)
def reschedule_appointment(
    appointment_id: int,
    payload: AppointmentReschedule,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AppointmentService(db)
    return service.reschedule(
        appointment_id, payload.scheduled_at, current_user, ip_address=get_client_ip(request)
    )


@router.patch("/{appointment_id}/status", response_model=AppointmentRead)
def update_appointment_status(
    appointment_id: int,
    payload: AppointmentStatusUpdate,
    request: Request,
    current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.DOCTOR, UserRole.NURSE, UserRole.RECEPTIONIST)
    ),
    db: Session = Depends(get_db),
):
    service = AppointmentService(db)
    return service.update_status(
        appointment_id, payload.status, current_user, ip_address=get_client_ip(request)
    )
