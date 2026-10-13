"""Repositorios de consulta e lista de espera."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select

from app.core.datetime_utils import day_bounds, range_bounds
from app.core.pagination import PaginationParams
from app.models.appointment import Appointment, WaitlistEntry
from app.models.enums import ACTIVE_APPOINTMENT_STATUSES, AppointmentStatus, WaitlistStatus
from app.repositories.base import BaseRepository

APPOINTMENT_SORT_FIELDS = {
    "id": Appointment.id,
    "scheduled_start": Appointment.scheduled_start,
    "status": Appointment.status,
    "created_at": Appointment.created_at,
    "updated_at": Appointment.updated_at,
}


class AppointmentRepository(BaseRepository[Appointment]):
    model = Appointment

    def find_conflicts(
        self,
        professional_id: int,
        start: datetime,
        end: datetime,
        *,
        exclude_id: int | None = None,
    ) -> list[Appointment]:
        """Consultas ativas do profissional que se sobrepoem ao intervalo."""
        stmt = select(Appointment).where(
            Appointment.professional_id == professional_id,
            Appointment.status.in_(list(ACTIVE_APPOINTMENT_STATUSES)),
            Appointment.scheduled_start < end,
            Appointment.scheduled_end > start,
        )
        if exclude_id:
            stmt = stmt.where(Appointment.id != exclude_id)
        return list(self.db.execute(stmt).scalars().all())

    def find_patient_conflicts(
        self,
        patient_id: int,
        start: datetime,
        end: datetime,
        *,
        exclude_id: int | None = None,
    ) -> list[Appointment]:
        stmt = select(Appointment).where(
            Appointment.patient_id == patient_id,
            Appointment.status.in_(list(ACTIVE_APPOINTMENT_STATUSES)),
            Appointment.scheduled_start < end,
            Appointment.scheduled_end > start,
        )
        if exclude_id:
            stmt = stmt.where(Appointment.id != exclude_id)
        return list(self.db.execute(stmt).scalars().all())

    def list_for_day(
        self, professional_id: int, day: date, *, include_cancelled: bool = False
    ) -> list[Appointment]:
        start, end = day_bounds(day)
        stmt = select(Appointment).where(
            Appointment.professional_id == professional_id,
            Appointment.scheduled_start >= start,
            Appointment.scheduled_start < end,
        )
        if not include_cancelled:
            stmt = stmt.where(Appointment.status != AppointmentStatus.CANCELLED)
        stmt = stmt.order_by(Appointment.scheduled_start.asc())
        return list(self.db.execute(stmt).scalars().all())

    def list_for_patient(self, patient_id: int) -> list[Appointment]:
        stmt = (
            select(Appointment)
            .where(Appointment.patient_id == patient_id)
            .order_by(Appointment.scheduled_start.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def search(
        self,
        pagination: PaginationParams,
        *,
        patient_id: int | None = None,
        professional_id: int | None = None,
        status: AppointmentStatus | None = None,
        statuses: list[AppointmentStatus] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[list[Appointment], int]:
        stmt = select(Appointment)
        if patient_id is not None:
            stmt = stmt.where(Appointment.patient_id == patient_id)
        if professional_id is not None:
            stmt = stmt.where(Appointment.professional_id == professional_id)
        if status is not None:
            stmt = stmt.where(Appointment.status == status)
        if statuses:
            stmt = stmt.where(Appointment.status.in_(statuses))

        start, end = range_bounds(start_date, end_date)
        if start is not None:
            stmt = stmt.where(Appointment.scheduled_start >= start)
        if end is not None:
            stmt = stmt.where(Appointment.scheduled_start < end)

        column, descending = pagination.resolve_sort(APPOINTMENT_SORT_FIELDS, "scheduled_start")
        stmt = self.apply_order(stmt, column, descending)
        return self.paginate(stmt, pagination.page, pagination.size)


class WaitlistRepository(BaseRepository[WaitlistEntry]):
    model = WaitlistEntry

    def find_open_matches(self, professional_id: int, slot_start: datetime) -> list[WaitlistEntry]:
        """Entradas abertas do profissional para a data do horario liberado."""
        stmt = (
            select(WaitlistEntry)
            .where(
                WaitlistEntry.professional_id == professional_id,
                WaitlistEntry.desired_date == slot_start.date(),
                WaitlistEntry.status == WaitlistStatus.WAITING,
            )
            .order_by(WaitlistEntry.created_at.asc(), WaitlistEntry.id.asc())
        )
        entries = list(self.db.execute(stmt).scalars().all())
        return [entry for entry in entries if entry.matches_slot(slot_start)]

    def find_duplicate(
        self, patient_id: int, professional_id: int, desired_date: date
    ) -> WaitlistEntry | None:
        stmt = (
            select(WaitlistEntry)
            .where(
                WaitlistEntry.patient_id == patient_id,
                WaitlistEntry.professional_id == professional_id,
                WaitlistEntry.desired_date == desired_date,
                WaitlistEntry.status.in_([WaitlistStatus.WAITING, WaitlistStatus.NOTIFIED]),
            )
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def search(
        self,
        pagination: PaginationParams,
        *,
        patient_id: int | None = None,
        professional_id: int | None = None,
        status: WaitlistStatus | None = None,
        desired_date: date | None = None,
    ) -> tuple[list[WaitlistEntry], int]:
        stmt = select(WaitlistEntry)
        if patient_id is not None:
            stmt = stmt.where(WaitlistEntry.patient_id == patient_id)
        if professional_id is not None:
            stmt = stmt.where(WaitlistEntry.professional_id == professional_id)
        if status is not None:
            stmt = stmt.where(WaitlistEntry.status == status)
        if desired_date is not None:
            stmt = stmt.where(WaitlistEntry.desired_date == desired_date)
        stmt = stmt.order_by(WaitlistEntry.desired_date.asc(), WaitlistEntry.created_at.asc())
        return self.paginate(stmt, pagination.page, pagination.size)
