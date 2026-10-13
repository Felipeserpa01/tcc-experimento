from datetime import date, datetime, time, timedelta
from typing import Any, ClassVar

from sqlalchemy import select, update

from app.core.pagination import PageParams, PageResult, SortParams
from app.models.billing import Charge
from app.models.enums import ChargeStatus, PaymentMethod
from app.repositories.base import BaseRepository


class ChargeRepository(BaseRepository[Charge]):
    model = Charge
    sortable_columns: ClassVar[dict[str, Any]] = {
        "created_at": Charge.created_at,
        "paid_at": Charge.paid_at,
        "net_amount": Charge.net_amount,
    }

    def find_active_for_appointment(self, appointment_id: int) -> Charge | None:
        return self.db.scalar(
            select(Charge).where(Charge.appointment_id == appointment_id, Charge.status != ChargeStatus.CANCELLED)
        )

    def find_active_for_exam(self, exam_id: int) -> Charge | None:
        return self.db.scalar(select(Charge).where(Charge.exam_id == exam_id, Charge.status != ChargeStatus.CANCELLED))

    def transition_from_pending(self, charge_id: int, target: ChargeStatus, **values: object) -> bool:
        """Atualização condicional atômica: só altera se a cobrança ainda estiver pendente.

        Evita que duas requisições concorrentes registrem o mesmo pagamento duas vezes.
        """
        result = self.db.execute(
            update(Charge)
            .where(Charge.id == charge_id, Charge.status == ChargeStatus.PENDING)
            .values(status=target, **values)
            .execution_options(synchronize_session=False)
        )
        return result.rowcount == 1

    def search(
        self,
        page: PageParams,
        sort: SortParams,
        *,
        patient_id: int | None = None,
        status: ChargeStatus | None = None,
        payment_method: PaymentMethod | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> PageResult[Charge]:
        stmt = select(Charge)
        if patient_id is not None:
            stmt = stmt.where(Charge.patient_id == patient_id)
        if status is not None:
            stmt = stmt.where(Charge.status == status)
        if payment_method is not None:
            stmt = stmt.where(Charge.payment_method == payment_method)
        if date_from is not None:
            stmt = stmt.where(Charge.created_at >= datetime.combine(date_from, time.min))
        if date_to is not None:
            stmt = stmt.where(Charge.created_at < datetime.combine(date_to, time.min) + timedelta(days=1))
        return self.paginate(stmt, page, sort)
