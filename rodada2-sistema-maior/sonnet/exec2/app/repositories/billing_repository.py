"""Data access for Billing."""
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from app.core.enums import BillingStatus, PaymentMethod
from app.models.billing import Billing

SORTABLE_FIELDS = {
    "created_at": Billing.created_at,
    "valor_final": Billing.valor_final,
    "status": Billing.status,
}


class BillingRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, billing_id: int) -> Billing | None:
        return self.db.get(Billing, billing_id)

    def get_by_appointment_id(self, appointment_id: int) -> Billing | None:
        stmt = select(Billing).where(
            Billing.appointment_id == appointment_id, Billing.status != BillingStatus.CANCELADO
        )
        return self.db.execute(stmt).scalars().first()

    def get_by_exam_id(self, exam_id: int) -> Billing | None:
        stmt = select(Billing).where(
            Billing.exam_id == exam_id, Billing.status != BillingStatus.CANCELADO
        )
        return self.db.execute(stmt).scalars().first()

    def create(self, billing: Billing) -> Billing:
        self.db.add(billing)
        self.db.flush()
        return billing

    def update(self, billing: Billing) -> Billing:
        self.db.add(billing)
        self.db.flush()
        return billing

    def search(
        self,
        patient_id: int | None,
        status: BillingStatus | None,
        page: int,
        page_size: int,
        sort_by: str | None,
        sort_order: str,
    ) -> tuple[list[Billing], int]:
        stmt = select(Billing)
        if patient_id:
            stmt = stmt.where(Billing.patient_id == patient_id)
        if status:
            stmt = stmt.where(Billing.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()

        sort_column = SORTABLE_FIELDS.get(sort_by or "created_at", Billing.created_at)
        order_func = desc if sort_order == "desc" else asc
        stmt = stmt.order_by(order_func(sort_column)).offset((page - 1) * page_size).limit(page_size)

        items = list(self.db.execute(stmt).scalars().all())
        return items, total

    def revenue_by_period(self, date_from: date, date_to: date) -> list[tuple[date, Decimal]]:
        stmt = (
            select(func.date(Billing.paid_at), func.sum(Billing.valor_final))
            .where(
                Billing.status == BillingStatus.PAGO,
                Billing.paid_at >= datetime.combine(date_from, datetime.min.time()),
                Billing.paid_at < datetime.combine(date_to, datetime.min.time()) + timedelta(days=1),
            )
            .group_by(func.date(Billing.paid_at))
            .order_by(func.date(Billing.paid_at))
        )
        return list(self.db.execute(stmt).all())

    def revenue_by_payment_method(self, date_from: date, date_to: date) -> list[tuple[PaymentMethod, Decimal]]:
        stmt = (
            select(Billing.forma_pagamento, func.sum(Billing.valor_final))
            .where(
                Billing.status == BillingStatus.PAGO,
                Billing.paid_at >= datetime.combine(date_from, datetime.min.time()),
                Billing.paid_at < datetime.combine(date_to, datetime.min.time()) + timedelta(days=1),
            )
            .group_by(Billing.forma_pagamento)
        )
        return list(self.db.execute(stmt).all())
