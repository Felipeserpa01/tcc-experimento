"""Billing endpoints."""
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.enums import BillingStatus, UserRole
from app.database import get_db
from app.dependencies import get_client_ip, get_current_user, require_roles
from app.models.user import User
from app.schemas.billing import BillingCreate, BillingOut, BillingPayment
from app.schemas.common import PaginatedResponse
from app.services.billing_service import BillingService

router = APIRouter(prefix="/billing", tags=["Faturamento"])

BILLING_MANAGE_ROLES = (UserRole.ADMIN, UserRole.RECEPCIONISTA)


@router.post("", response_model=BillingOut, status_code=status.HTTP_201_CREATED)
def create_billing(
    payload: BillingCreate,
    request: Request,
    current_user: User = Depends(require_roles(*BILLING_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    service = BillingService(db)
    return service.create(payload, current_user, ip_address=get_client_ip(request))


@router.get("", response_model=PaginatedResponse[BillingOut])
def search_billing(
    patient_id: int | None = None,
    status_filter: BillingStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str | None = None,
    sort_order: Literal["asc", "desc"] = "asc",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BillingService(db)
    items, total = service.search(
        current_user, patient_id, status_filter, page, page_size, sort_by, sort_order
    )
    return PaginatedResponse.build(items, total, page, page_size)


@router.get("/{billing_id}", response_model=BillingOut)
def get_billing(
    billing_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    service = BillingService(db)
    return service.get(billing_id, current_user)


@router.post("/{billing_id}/pay", response_model=BillingOut)
def pay_billing(
    billing_id: int,
    payload: BillingPayment,
    request: Request,
    current_user: User = Depends(require_roles(*BILLING_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    service = BillingService(db)
    return service.pay(billing_id, payload, current_user, ip_address=get_client_ip(request))


@router.post("/{billing_id}/cancel", response_model=BillingOut)
def cancel_billing(
    billing_id: int,
    request: Request,
    current_user: User = Depends(require_roles(*BILLING_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    service = BillingService(db)
    return service.cancel(billing_id, current_user, ip_address=get_client_ip(request))
