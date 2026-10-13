"""Schemas de faturamento."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.enums import ChargeStatus, ChargeType, PaymentMethod
from app.schemas.common import ORMModel


class ChargeCreate(BaseModel):
    patient_id: int | None = Field(
        None, description="Opcional quando `appointment_id` ou `exam_id` e informado"
    )
    appointment_id: int | None = None
    exam_id: int | None = None
    charge_type: ChargeType = ChargeType.APPOINTMENT
    description: str | None = Field(None, max_length=255)
    gross_amount: Decimal | None = Field(
        None, ge=0, le=Decimal("99999999.99"),
        description="Se omitido, usa o valor da consulta do profissional ou o preco do exame",
    )
    payment_method: PaymentMethod | None = None
    due_date: datetime | None = None
    apply_insurance_discount: bool = True

    @model_validator(mode="after")
    def _validate_origin(self) -> "ChargeCreate":
        if self.charge_type == ChargeType.APPOINTMENT and not self.appointment_id:
            raise ValueError("Cobranca de consulta exige `appointment_id`.")
        if self.charge_type == ChargeType.EXAM and not self.exam_id:
            raise ValueError("Cobranca de exame exige `exam_id`.")
        if self.charge_type == ChargeType.OTHER:
            if not self.patient_id:
                raise ValueError("Cobranca avulsa exige `patient_id`.")
            if self.gross_amount is None:
                raise ValueError("Cobranca avulsa exige `gross_amount`.")
            if not self.description:
                raise ValueError("Cobranca avulsa exige `description`.")
        if self.appointment_id and self.exam_id:
            raise ValueError("Informe apenas `appointment_id` OU `exam_id`.")
        return self


class ChargePaymentRequest(BaseModel):
    payment_method: PaymentMethod
    amount: Decimal | None = Field(
        None, ge=0, le=Decimal("99999999.99"),
        description="Se omitido, considera o valor liquido total da cobranca",
    )
    payment_reference: str | None = Field(None, max_length=120)


class ChargeCancelRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=255)


class ChargeRead(ORMModel):
    id: int
    patient_id: int
    appointment_id: int | None = None
    exam_id: int | None = None
    charge_type: ChargeType
    description: str
    gross_amount: Decimal
    discount_percent: Decimal
    discount_amount: Decimal
    net_amount: Decimal
    status: ChargeStatus
    payment_method: PaymentMethod | None = None
    insurance_name: str | None = None
    due_date: datetime | None = None
    paid_at: datetime | None = None
    paid_amount: Decimal | None = None
    payment_reference: str | None = None
    cancelled_at: datetime | None = None
    cancellation_reason: str | None = None
    created_by_id: int | None = None
    paid_by_id: int | None = None
    created_at: datetime
    updated_at: datetime
