from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.billing import Billing
from app.models.enums import BillingStatus, PaymentMethod


class BillingRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, billing_id: int) -> Billing | None:
        return self.db.get(Billing, billing_id)

    def get_by_appointment_id(self, appointment_id: int) -> list[Billing]:
        stmt = select(Billing).where(Billing.appointment_id == appointment_id)
        return self.db.execute(stmt).scalars().all()

    def search(
        self,
        status: BillingStatus | None,
        payment_method: PaymentMethod | None,
        start: date | None,
        end: date | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Billing], int]:
        stmt = select(Billing)
        if status:
            stmt = stmt.where(Billing.status == status)
        if payment_method:
            stmt = stmt.where(Billing.payment_method == payment_method)
        if start:
            stmt = stmt.where(Billing.created_at >= datetime.combine(start, datetime.min.time()))
        if end:
            stmt = stmt.where(Billing.created_at <= datetime.combine(end, datetime.max.time()))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()

        stmt = stmt.order_by(Billing.created_at.desc()).offset(offset).limit(limit)
        items = self.db.execute(stmt).scalars().all()
        return items, total

    def create(self, billing: Billing) -> Billing:
        self.db.add(billing)
        self.db.commit()
        self.db.refresh(billing)
        return billing

    def update(self, billing: Billing) -> Billing:
        self.db.commit()
        self.db.refresh(billing)
        return billing

    def list_between(self, start: date, end: date) -> list[Billing]:
        stmt = select(Billing).where(
            Billing.created_at >= datetime.combine(start, datetime.min.time()),
            Billing.created_at <= datetime.combine(end, datetime.max.time()),
        )
        return self.db.execute(stmt).scalars().all()
