from datetime import date

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, get_current_user, require_roles
from app.core.permissions import MANAGEMENT_ROLES
from app.database import get_db
from app.models.enums import BillingStatus, PaymentMethod, UserRole
from app.models.user import User
from app.schemas.billing import BillingCreate, BillingPayRequest, BillingRead
from app.schemas.common import Page
from app.services.billing_service import BillingService
from app.utils.pagination import PageParams

router = APIRouter(prefix="/billing", tags=["Faturamento"])


@router.post("", response_model=BillingRead, status_code=status.HTTP_201_CREATED)
def create_billing(
    payload: BillingCreate,
    request: Request,
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
    db: Session = Depends(get_db),
):
    service = BillingService(db)
    return service.create_billing(payload, current_user, ip_address=get_client_ip(request))


@router.get("", response_model=Page[BillingRead])
def search_billing(
    billing_status: BillingStatus | None = Query(None),
    payment_method: PaymentMethod | None = Query(None),
    start: date | None = Query(None),
    end: date | None = Query(None),
    params: PageParams = Depends(),
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
    db: Session = Depends(get_db),
):
    service = BillingService(db)
    items, total = service.search(
        billing_status, payment_method, start, end, params.offset, params.page_size
    )
    return Page(total=total, page=params.page, page_size=params.page_size, items=items)


@router.get("/{billing_id}", response_model=BillingRead)
def get_billing(
    billing_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = BillingService(db)
    return service.get_billing(billing_id, current_user)


@router.patch("/{billing_id}/pay", response_model=BillingRead)
def pay_billing(
    billing_id: int,
    payload: BillingPayRequest,
    request: Request,
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
    db: Session = Depends(get_db),
):
    service = BillingService(db)
    return service.pay(
        billing_id, current_user, payment_method=payload.payment_method, ip_address=get_client_ip(request)
    )


@router.patch("/{billing_id}/cancel", response_model=BillingRead)
def cancel_billing(
    billing_id: int,
    request: Request,
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
    db: Session = Depends(get_db),
):
    service = BillingService(db)
    return service.cancel(billing_id, current_user, ip_address=get_client_ip(request))
