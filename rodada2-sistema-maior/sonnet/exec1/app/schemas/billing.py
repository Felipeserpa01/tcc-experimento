from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BillingStatus, PaymentMethod


class BillingCreate(BaseModel):
    appointment_id: int
    amount: Decimal = Field(gt=0)
    discount: Decimal = Field(default=Decimal("0"), ge=0)
    payment_method: PaymentMethod


class BillingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    appointment_id: int
    amount: Decimal
    discount: Decimal
    final_amount: Decimal
    payment_method: PaymentMethod
    status: BillingStatus
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime


class BillingPayRequest(BaseModel):
    payment_method: PaymentMethod | None = None
