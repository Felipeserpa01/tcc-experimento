"""Data access for Appointment and WaitlistEntry."""
from datetime import date, datetime, timedelta

from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from app.core.enums import AppointmentStatus, WaitlistStatus
from app.models.appointment import Appointment, WaitlistEntry

SORTABLE_FIELDS = {
    "data_hora": Appointment.data_hora,
    "status": Appointment.status,
    "created_at": Appointment.created_at,
}


class AppointmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, appointment_id: int) -> Appointment | None:
        return self.db.get(Appointment, appointment_id)

    def create(self, appointment: Appointment) -> Appointment:
        self.db.add(appointment)
        self.db.flush()
        return appointment

    def update(self, appointment: Appointment) -> Appointment:
        self.db.add(appointment)
        self.db.flush()
        return appointment

    def find_conflict(
        self,
        professional_id: int,
        start: datetime,
        end: datetime,
        exclude_appointment_id: int | None = None,
    ) -> Appointment | None:
        """Finds an active appointment for the professional overlapping [start, end)."""
        stmt = select(Appointment).where(
            Appointment.professional_id == professional_id,
            Appointment.status.not_in(
                [AppointmentStatus.CANCELADA, AppointmentStatus.FALTOU]
            ),
        )
        if exclude_appointment_id:
            stmt = stmt.where(Appointment.id != exclude_appointment_id)
        candidates = self.db.execute(stmt).scalars().all()
        for appt in candidates:
            existing_start = appt.data_hora
            existing_end = existing_start + timedelta(minutes=appt.duracao_minutos)
            if start < existing_end and end > existing_start:
                return appt
        return None

    def get_daily_agenda(self, professional_id: int, day: date) -> list[Appointment]:
        start = datetime.combine(day, datetime.min.time())
        end = start + timedelta(days=1)
        stmt = (
            select(Appointment)
            .where(
                Appointment.professional_id == professional_id,
                Appointment.data_hora >= start,
                Appointment.data_hora < end,
            )
            .order_by(asc(Appointment.data_hora))
        )
        return list(self.db.execute(stmt).scalars().all())

    def search(
        self,
        patient_id: int | None,
        professional_id: int | None,
        status: AppointmentStatus | None,
        date_from: date | None,
        date_to: date | None,
        page: int,
        page_size: int,
        sort_by: str | None,
        sort_order: str,
    ) -> tuple[list[Appointment], int]:
        stmt = select(Appointment)
        if patient_id:
            stmt = stmt.where(Appointment.patient_id == patient_id)
        if professional_id:
            stmt = stmt.where(Appointment.professional_id == professional_id)
        if status:
            stmt = stmt.where(Appointment.status == status)
        if date_from:
            stmt = stmt.where(Appointment.data_hora >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            stmt = stmt.where(
                Appointment.data_hora < datetime.combine(date_to, datetime.min.time()) + timedelta(days=1)
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()

        sort_column = SORTABLE_FIELDS.get(sort_by or "data_hora", Appointment.data_hora)
        order_func = desc if sort_order == "desc" else asc
        stmt = stmt.order_by(order_func(sort_column)).offset((page - 1) * page_size).limit(page_size)

        items = list(self.db.execute(stmt).scalars().all())
        return items, total

    # Waitlist
    def create_waitlist_entry(self, entry: WaitlistEntry) -> WaitlistEntry:
        self.db.add(entry)
        self.db.flush()
        return entry

    def get_waitlist_entry(self, entry_id: int) -> WaitlistEntry | None:
        return self.db.get(WaitlistEntry, entry_id)

    def update_waitlist_entry(self, entry: WaitlistEntry) -> WaitlistEntry:
        self.db.add(entry)
        self.db.flush()
        return entry

    def get_waiting_for_professional_and_date(
        self, professional_id: int, day: date
    ) -> list[WaitlistEntry]:
        stmt = (
            select(WaitlistEntry)
            .where(
                WaitlistEntry.professional_id == professional_id,
                WaitlistEntry.data_desejada == day,
                WaitlistEntry.status == WaitlistStatus.AGUARDANDO,
            )
            .order_by(asc(WaitlistEntry.created_at))
        )
        return list(self.db.execute(stmt).scalars().all())
