from collections.abc import Iterable
from datetime import date, datetime, time, timedelta
from typing import Any, ClassVar

from sqlalchemy import func, select, update

from app.core.pagination import PageParams, PageResult, SortParams
from app.models.appointment import Appointment, WaitlistEntry
from app.models.enums import (
    ACTIVE_APPOINTMENT_STATUSES,
    OPEN_WAITLIST_STATUSES,
    AppointmentStatus,
    WaitlistStatus,
)
from app.repositories.base import BaseRepository


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min)
    return start, start + timedelta(days=1)


class AppointmentRepository(BaseRepository[Appointment]):
    model = Appointment
    sortable_columns: ClassVar[dict[str, Any]] = {
        "start_at": Appointment.start_at,
        "created_at": Appointment.created_at,
        "status": Appointment.status,
    }

    def find_overlapping(
        self,
        start: datetime,
        end: datetime,
        *,
        professional_id: int | None = None,
        patient_id: int | None = None,
        exclude_id: int | None = None,
    ) -> list[Appointment]:
        """Consultas ativas que se sobrepõem ao intervalo [start, end)."""
        stmt = select(Appointment).where(
            Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
            Appointment.start_at < end,
            Appointment.end_at > start,
        )
        if professional_id is not None:
            stmt = stmt.where(Appointment.professional_id == professional_id)
        if patient_id is not None:
            stmt = stmt.where(Appointment.patient_id == patient_id)
        if exclude_id is not None:
            stmt = stmt.where(Appointment.id != exclude_id)
        return list(self.db.scalars(stmt).all())

    def list_for_professional_on(
        self, professional_id: int, day: date, *, statuses: Iterable[AppointmentStatus] | None = None
    ) -> list[Appointment]:
        day_start, day_end = _day_bounds(day)
        stmt = select(Appointment).where(
            Appointment.professional_id == professional_id,
            Appointment.start_at >= day_start,
            Appointment.start_at < day_end,
        )
        if statuses is not None:
            stmt = stmt.where(Appointment.status.in_(list(statuses)))
        return list(self.db.scalars(stmt.order_by(Appointment.start_at)).all())

    def count_future_active(
        self, *, patient_id: int | None = None, professional_id: int | None = None, after: datetime
    ) -> int:
        stmt = select(func.count(Appointment.id)).where(
            Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES), Appointment.start_at >= after
        )
        if patient_id is not None:
            stmt = stmt.where(Appointment.patient_id == patient_id)
        if professional_id is not None:
            stmt = stmt.where(Appointment.professional_id == professional_id)
        return self.db.scalar(stmt) or 0

    def search(
        self,
        page: PageParams,
        sort: SortParams,
        *,
        patient_id: int | None = None,
        professional_id: int | None = None,
        status: AppointmentStatus | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> PageResult[Appointment]:
        stmt = select(Appointment)
        if patient_id is not None:
            stmt = stmt.where(Appointment.patient_id == patient_id)
        if professional_id is not None:
            stmt = stmt.where(Appointment.professional_id == professional_id)
        if status is not None:
            stmt = stmt.where(Appointment.status == status)
        if date_from is not None:
            stmt = stmt.where(Appointment.start_at >= _day_bounds(date_from)[0])
        if date_to is not None:
            stmt = stmt.where(Appointment.start_at < _day_bounds(date_to)[1])
        return self.paginate(stmt, page, sort)

    def list_for_patient(self, patient_id: int, date_from: date | None, date_to: date | None) -> list[Appointment]:
        stmt = select(Appointment).where(Appointment.patient_id == patient_id)
        if date_from is not None:
            stmt = stmt.where(Appointment.start_at >= _day_bounds(date_from)[0])
        if date_to is not None:
            stmt = stmt.where(Appointment.start_at < _day_bounds(date_to)[1])
        return list(self.db.scalars(stmt.order_by(Appointment.start_at, Appointment.id)).all())


class WaitlistRepository(BaseRepository[WaitlistEntry]):
    model = WaitlistEntry
    sortable_columns: ClassVar[dict[str, Any]] = {
        "created_at": WaitlistEntry.created_at,
        "desired_start_at": WaitlistEntry.desired_start_at,
    }

    def find_open_overlapping(
        self,
        professional_id: int,
        start: datetime,
        end: datetime,
        *,
        patient_id: int | None = None,
    ) -> list[WaitlistEntry]:
        """Entradas abertas (aguardando/notificado) cujo horário desejado se sobrepõe a [start, end), em ordem FIFO."""
        stmt = select(WaitlistEntry).where(
            WaitlistEntry.professional_id == professional_id,
            WaitlistEntry.status.in_(OPEN_WAITLIST_STATUSES),
            WaitlistEntry.desired_start_at < end,
            WaitlistEntry.desired_end_at > start,
        )
        if patient_id is not None:
            stmt = stmt.where(WaitlistEntry.patient_id == patient_id)
        return list(self.db.scalars(stmt.order_by(WaitlistEntry.created_at, WaitlistEntry.id)).all())

    def expire_past_entries(self, now: datetime) -> None:
        self.db.execute(
            update(WaitlistEntry)
            .where(WaitlistEntry.status.in_(OPEN_WAITLIST_STATUSES), WaitlistEntry.desired_start_at <= now)
            .values(status=WaitlistStatus.EXPIRED, updated_at=now)
        )

    def search(
        self,
        page: PageParams,
        sort: SortParams,
        *,
        patient_id: int | None = None,
        professional_id: int | None = None,
        status: WaitlistStatus | None = None,
    ) -> PageResult[WaitlistEntry]:
        stmt = select(WaitlistEntry)
        if patient_id is not None:
            stmt = stmt.where(WaitlistEntry.patient_id == patient_id)
        if professional_id is not None:
            stmt = stmt.where(WaitlistEntry.professional_id == professional_id)
        if status is not None:
            stmt = stmt.where(WaitlistEntry.status == status)
        return self.paginate(stmt, page, sort)
