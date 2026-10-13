from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment, WaitListEntry
from app.models.enums import AppointmentStatus


class AppointmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, appointment_id: int) -> Appointment | None:
        return self.db.get(Appointment, appointment_id)

    def find_conflicting(
        self, doctor_id: int, start: datetime, end: datetime, exclude_id: int | None = None
    ) -> Appointment | None:
        """Finds an active appointment for the doctor whose interval overlaps [start, end)."""
        stmt = select(Appointment).where(
            Appointment.doctor_id == doctor_id,
            Appointment.status.notin_(
                [AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW]
            ),
        )
        if exclude_id is not None:
            stmt = stmt.where(Appointment.id != exclude_id)

        naive_start = start.replace(tzinfo=None)
        naive_end = end.replace(tzinfo=None)

        candidates = self.db.execute(stmt).scalars().all()
        for appt in candidates:
            existing_start = appt.scheduled_at.replace(tzinfo=None)
            existing_end = existing_start + timedelta(minutes=appt.duration_minutes)
            if naive_start < existing_end and existing_start < naive_end:
                return appt
        return None

    def search(
        self,
        patient_id: int | None,
        doctor_id: int | None,
        status: AppointmentStatus | None,
        start: datetime | None,
        end: datetime | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Appointment], int]:
        stmt = select(Appointment)
        if patient_id:
            stmt = stmt.where(Appointment.patient_id == patient_id)
        if doctor_id:
            stmt = stmt.where(Appointment.doctor_id == doctor_id)
        if status:
            stmt = stmt.where(Appointment.status == status)
        if start:
            stmt = stmt.where(Appointment.scheduled_at >= start)
        if end:
            stmt = stmt.where(Appointment.scheduled_at <= end)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()

        stmt = stmt.order_by(Appointment.scheduled_at.asc()).offset(offset).limit(limit)
        items = self.db.execute(stmt).scalars().all()
        return items, total

    def get_doctor_day_agenda(self, doctor_id: int, day: date) -> list[Appointment]:
        start = datetime.combine(day, datetime.min.time())
        end = datetime.combine(day, datetime.max.time())
        stmt = (
            select(Appointment)
            .where(
                Appointment.doctor_id == doctor_id,
                Appointment.scheduled_at >= start,
                Appointment.scheduled_at <= end,
            )
            .order_by(Appointment.scheduled_at.asc())
        )
        return self.db.execute(stmt).scalars().all()

    def create(self, appointment: Appointment) -> Appointment:
        self.db.add(appointment)
        self.db.commit()
        self.db.refresh(appointment)
        return appointment

    def update(self, appointment: Appointment) -> Appointment:
        self.db.commit()
        self.db.refresh(appointment)
        return appointment

    def add_waitlist_entry(self, entry: WaitListEntry) -> WaitListEntry:
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def get_waitlist_for_doctor(self, doctor_id: int, desired_date: date) -> list[WaitListEntry]:
        stmt = select(WaitListEntry).where(
            WaitListEntry.doctor_id == doctor_id,
            WaitListEntry.desired_date == desired_date,
            WaitListEntry.notified.is_(False),
        )
        return self.db.execute(stmt).scalars().all()

    def list_waitlist(self, offset: int, limit: int) -> tuple[list[WaitListEntry], int]:
        total = self.db.execute(select(WaitListEntry)).scalars().all()
        stmt = select(WaitListEntry).order_by(WaitListEntry.created_at.asc()).offset(offset).limit(limit)
        items = self.db.execute(stmt).scalars().all()
        return items, len(total)
