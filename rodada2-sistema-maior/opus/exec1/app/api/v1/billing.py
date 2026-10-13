"""Rotas de faturamento."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.pagination import Page, PaginationParams
from app.db.session import get_db
from app.models.enums import ChargeStatus, ChargeType, PaymentMethod
from app.models.user import User
from app.schemas.billing import (
    ChargeCancelRequest,
    ChargeCreate,
    ChargePaymentRequest,
    ChargeRead,
)
from app.services.billing_service import BillingService

router = APIRouter(prefix="/charges", tags=["Faturamento"])


@router.post(
    "",
    response_model=ChargeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Gera cobranca de consulta, exame ou servico avulso",
    description="O desconto do convenio do paciente e aplicado automaticamente quando existir.",
)
def create_charge(
    payload: ChargeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChargeRead:
    return ChargeRead.model_validate(BillingService(db).create(payload, current_user))


@router.get("", response_model=Page[ChargeRead], summary="Lista cobrancas com filtros")
def list_charges(
    pagination: PaginationParams = Depends(),
    patient_id: int | None = Query(None),
    appointment_id: int | None = Query(None),
    charge_status: ChargeStatus | None = Query(None, alias="status"),
    charge_type: ChargeType | None = Query(None),
    payment_method: PaymentMethod | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[ChargeRead]:
    items, total = BillingService(db).search(
        pagination,
        current_user,
        patient_id=patient_id,
        appointment_id=appointment_id,
        status=charge_status,
        charge_type=charge_type,
        payment_method=payment_method,
        start_date=start_date,
        end_date=end_date,
    )
    return Page.create(
        [ChargeRead.model_validate(item) for item in items],
        total,
        pagination.page,
        pagination.size,
    )


@router.get("/{charge_id}", response_model=ChargeRead, summary="Detalha uma cobranca")
def get_charge(
    charge_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChargeRead:
    return ChargeRead.model_validate(BillingService(db).get(charge_id, current_user))


@router.post(
    "/{charge_id}/pay",
    response_model=ChargeRead,
    summary="Registra o pagamento",
    description="Retorna 409 quando a cobranca ja foi paga ou esta cancelada.",
)
def pay_charge(
    charge_id: int,
    payload: ChargePaymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChargeRead:
    return ChargeRead.model_validate(
        BillingService(db).register_payment(charge_id, payload, current_user)
    )


@router.post("/{charge_id}/cancel", response_model=ChargeRead, summary="Cancela uma cobranca")
def cancel_charge(
    charge_id: int,
    payload: ChargeCancelRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChargeRead:
    return ChargeRead.model_validate(BillingService(db).cancel(charge_id, payload, current_user))
