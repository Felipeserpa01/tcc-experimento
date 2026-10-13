"""Repositorio de cobrancas."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select

from app.core.datetime_utils import range_bounds
from app.core.pagination import PaginationParams
from app.models.billing import Charge
from app.models.enums import ChargeStatus, ChargeType, PaymentMethod
from app.repositories.base import BaseRepository

CHARGE_SORT_FIELDS = {
    "id": Charge.id,
    "net_amount": Charge.net_amount,
    "status": Charge.status,
    "created_at": Charge.created_at,
    "paid_at": Charge.paid_at,
    "due_date": Charge.due_date,
}


class ChargeRepository(BaseRepository[Charge]):
    model = Charge

    def list_for_appointment(self, appointment_id: int) -> list[Charge]:
        stmt = select(Charge).where(Charge.appointment_id == appointment_id)
        return list(self.db.execute(stmt).scalars().all())

    def list_for_exam(self, exam_id: int) -> list[Charge]:
        stmt = select(Charge).where(Charge.exam_id == exam_id)
        return list(self.db.execute(stmt).scalars().all())

    def has_open_charge_for_appointment(self, appointment_id: int) -> bool:
        stmt = (
            select(Charge.id)
            .where(
                Charge.appointment_id == appointment_id,
                Charge.status != ChargeStatus.CANCELLED,
            )
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first() is not None

    def has_open_charge_for_exam(self, exam_id: int) -> bool:
        stmt = (
            select(Charge.id)
            .where(Charge.exam_id == exam_id, Charge.status != ChargeStatus.CANCELLED)
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first() is not None

    def search(
        self,
        pagination: PaginationParams,
        *,
        patient_id: int | None = None,
        appointment_id: int | None = None,
        status: ChargeStatus | None = None,
        charge_type: ChargeType | None = None,
        payment_method: PaymentMethod | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[list[Charge], int]:
        stmt = select(Charge)
        if patient_id is not None:
            stmt = stmt.where(Charge.patient_id == patient_id)
        if appointment_id is not None:
            stmt = stmt.where(Charge.appointment_id == appointment_id)
        if status is not None:
            stmt = stmt.where(Charge.status == status)
        if charge_type is not None:
            stmt = stmt.where(Charge.charge_type == charge_type)
        if payment_method is not None:
            stmt = stmt.where(Charge.payment_method == payment_method)

        start, end = range_bounds(start_date, end_date)
        if start is not None:
            stmt = stmt.where(Charge.created_at >= start)
        if end is not None:
            stmt = stmt.where(Charge.created_at < end)

        column, descending = pagination.resolve_sort(CHARGE_SORT_FIELDS, "created_at")
        stmt = self.apply_order(stmt, column, descending)
        return self.paginate(stmt, pagination.page, pagination.size)
