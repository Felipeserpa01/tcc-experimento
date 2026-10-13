from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import ERROR_RESPONSES, Pagination, get_billing_service, require, sorting
from app.core.pagination import SortOrder, SortParams
from app.core.permissions import Permission
from app.models.enums import ChargeStatus, PaymentMethod
from app.models.user import User
from app.schemas.billing import ChargeCancel, ChargeCreate, ChargeOut, ChargePayment
from app.schemas.common import Page
from app.services.billing_service import BillingService

router = APIRouter(prefix="/billing/charges", tags=["Faturamento"], responses=ERROR_RESPONSES)

Billing = Annotated[BillingService, Depends(get_billing_service)]
Reader = Annotated[User, Depends(require(Permission.BILLING_READ))]
Manager = Annotated[User, Depends(require(Permission.BILLING_MANAGE))]
ChargeSort = Annotated[
    SortParams,
    Depends(sorting("created_at", "paid_at", "net_amount", default="created_at", default_order=SortOrder.DESC)),
]


@router.post("", response_model=ChargeOut, status_code=status.HTTP_201_CREATED, summary="Gerar cobrança")
def create_charge(data: ChargeCreate, actor: Manager, service: Billing) -> object:
    """Gera a cobrança de uma consulta ou exame. O desconto do convênio ativo do paciente é aplicado automaticamente."""
    return service.create(actor, data)


@router.get("", response_model=Page[ChargeOut], summary="Listar cobranças")
def list_charges(
    actor: Reader,
    service: Billing,
    page: Pagination,
    sort: ChargeSort,
    patient_id: Annotated[int | None, Query(gt=0)] = None,
    status_filter: Annotated[ChargeStatus | None, Query(alias="status")] = None,
    payment_method: PaymentMethod | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> object:
    return service.search(
        actor,
        page,
        sort,
        patient_id=patient_id,
        status=status_filter,
        payment_method=payment_method,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/{charge_id}", response_model=ChargeOut, summary="Detalhar cobrança")
def get_charge(charge_id: int, actor: Reader, service: Billing) -> object:
    return service.get(actor, charge_id)


@router.post("/{charge_id}/pay", response_model=ChargeOut, summary="Registrar pagamento")
def pay_charge(charge_id: int, data: ChargePayment, actor: Manager, service: Billing) -> object:
    """Uma cobrança já paga não pode ser paga novamente (409)."""
    return service.pay(actor, charge_id, data)


@router.post("/{charge_id}/cancel", response_model=ChargeOut, summary="Cancelar cobrança pendente")
def cancel_charge(charge_id: int, data: ChargeCancel, actor: Manager, service: Billing) -> object:
    return service.cancel(actor, charge_id, data.reason)
