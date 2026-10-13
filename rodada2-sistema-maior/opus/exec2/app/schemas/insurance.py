from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, Field

from app.schemas.common import InputSchema, NonNull, OutputSchema
from app.utils.money import to_money
from app.utils.validators import validate_ans_code

DiscountPercent = Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2), AfterValidator(to_money)]
AnsCode = Annotated[str, AfterValidator(validate_ans_code)]


class InsuranceCreate(InputSchema):
    name: str = Field(min_length=2, max_length=100)
    ans_code: AnsCode | None = None
    discount_percent: DiscountPercent = Decimal("0")
    is_active: bool = True


class InsuranceUpdate(InputSchema):
    name: Annotated[str | None, NonNull, Field(min_length=2, max_length=100)] = None
    ans_code: AnsCode | None = None
    discount_percent: Annotated[DiscountPercent | None, NonNull] = None
    is_active: Annotated[bool | None, NonNull] = None


class InsuranceSummary(OutputSchema):
    id: int
    name: str
    discount_percent: Decimal


class InsuranceOut(InsuranceSummary):
    ans_code: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
