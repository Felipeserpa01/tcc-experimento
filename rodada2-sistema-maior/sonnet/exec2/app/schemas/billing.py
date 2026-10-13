"""Billing schemas."""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.enums import BillableType, BillingStatus, PaymentMethod


class BillingCreate(BaseModel):
    patient_id: int
    appointment_id: int | None = None
    exam_id: int | None = None
    tipo: BillableType
    valor: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    forma_pagamento: PaymentMethod
    aplicar_desconto_convenio: bool = False

    @model_validator(mode="after")
    def validate_reference(self) -> "BillingCreate":
        if self.tipo == BillableType.CONSULTA and not self.appointment_id:
            raise ValueError("appointment_id é obrigatório para cobrança de consulta.")
        if self.tipo == BillableType.EXAME and not self.exam_id:
            raise ValueError("exam_id é obrigatório para cobrança de exame.")
        return self


class BillingPayment(BaseModel):
    forma_pagamento: PaymentMethod | None = None


class BillingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    appointment_id: int | None
    exam_id: int | None
    tipo: BillableType
    valor: Decimal
    valor_desconto: Decimal
    valor_final: Decimal
    convenio_aplicado: bool
    forma_pagamento: PaymentMethod
    status: BillingStatus
    created_by: int
    created_at: datetime
    paid_at: datetime | None
