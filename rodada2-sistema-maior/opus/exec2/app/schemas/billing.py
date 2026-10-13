from datetime import datetime
from decimal import Decimal

from pydantic import Field, model_validator

from app.models.enums import ChargeStatus, PaymentMethod
from app.schemas.common import InputSchema, MoneyAmount, OutputSchema


class ChargeCreate(InputSchema):
    """Cobrança de uma consulta **ou** de um exame (exatamente um dos dois)."""

    appointment_id: int | None = Field(default=None, gt=0)
    exam_id: int | None = Field(default=None, gt=0)
    amount: MoneyAmount | None = Field(
        default=None,
        description="Valor bruto em R$. Para consultas, se omitido, usa o valor de consulta do médico.",
    )
    payment_method: PaymentMethod
    description: str | None = Field(default=None, min_length=3, max_length=255)

    @model_validator(mode="after")
    def _exactly_one_item(self) -> "ChargeCreate":
        if (self.appointment_id is None) == (self.exam_id is None):
            raise ValueError("Informe exatamente um item a cobrar: 'appointment_id' ou 'exam_id'.")
        return self


class ChargePayment(InputSchema):
    payment_method: PaymentMethod | None = Field(
        default=None, description="Forma de pagamento efetiva (se diferente da prevista)"
    )
    amount_paid: MoneyAmount | None = Field(
        default=None, description="Se informado, deve ser igual ao valor líquido da cobrança"
    )


class ChargeCancel(InputSchema):
    reason: str = Field(min_length=5, max_length=500)


class ChargeOut(OutputSchema):
    id: int
    patient_id: int
    patient_name: str
    appointment_id: int | None
    exam_id: int | None
    description: str
    gross_amount: Decimal
    discount_percent: Decimal
    discount_amount: Decimal
    net_amount: Decimal
    payment_method: PaymentMethod
    status: ChargeStatus
    insurance_id: int | None
    insurance_name: str | None
    paid_at: datetime | None
    paid_amount: Decimal | None
    cancelled_at: datetime | None
    cancellation_reason: str | None
    created_at: datetime
    updated_at: datetime
