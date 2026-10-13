"""Aggregation queries for reports and indicators."""
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import AppointmentStatus
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.models.professional import Professional


class ReportRepository:
    def __init__(self, db: Session):
        self.db = db

    def _period_bounds(self, date_from: date, date_to: date) -> tuple[datetime, datetime]:
        return (
            datetime.combine(date_from, datetime.min.time()),
            datetime.combine(date_to, datetime.min.time()) + timedelta(days=1),
        )

    def appointments_by_period(self, date_from: date, date_to: date) -> list[tuple[date, int]]:
        start, end = self._period_bounds(date_from, date_to)
        stmt = (
            select(func.date(Appointment.data_hora), func.count())
            .where(Appointment.data_hora >= start, Appointment.data_hora < end)
            .group_by(func.date(Appointment.data_hora))
            .order_by(func.date(Appointment.data_hora))
        )
        return list(self.db.execute(stmt).all())

    def appointments_by_professional(self, date_from: date, date_to: date) -> list[tuple[int, str, int]]:
        start, end = self._period_bounds(date_from, date_to)
        stmt = (
            select(Professional.id, Professional.nome, func.count(Appointment.id))
            .join(Appointment, Appointment.professional_id == Professional.id)
            .where(Appointment.data_hora >= start, Appointment.data_hora < end)
            .group_by(Professional.id, Professional.nome)
            .order_by(func.count(Appointment.id).desc())
        )
        return list(self.db.execute(stmt).all())

    def appointments_by_specialty(self, date_from: date, date_to: date) -> list[tuple[str, int]]:
        start, end = self._period_bounds(date_from, date_to)
        stmt = (
            select(Professional.especialidade, func.count(Appointment.id))
            .join(Appointment, Appointment.professional_id == Professional.id)
            .where(Appointment.data_hora >= start, Appointment.data_hora < end)
            .group_by(Professional.especialidade)
            .order_by(func.count(Appointment.id).desc())
        )
        return list(self.db.execute(stmt).all())

    def appointments_by_status(self, date_from: date, date_to: date) -> list[tuple[AppointmentStatus, int]]:
        start, end = self._period_bounds(date_from, date_to)
        stmt = (
            select(Appointment.status, func.count())
            .where(Appointment.data_hora >= start, Appointment.data_hora < end)
            .group_by(Appointment.status)
        )
        return list(self.db.execute(stmt).all())

    def no_show_rate_by_professional(self, date_from: date, date_to: date) -> list[tuple[int, str, int, int]]:
        start, end = self._period_bounds(date_from, date_to)
        total_stmt = (
            select(Professional.id, Professional.nome, func.count(Appointment.id))
            .join(Appointment, Appointment.professional_id == Professional.id)
            .where(Appointment.data_hora >= start, Appointment.data_hora < end)
            .group_by(Professional.id, Professional.nome)
        )
        totals = {row[0]: (row[1], row[2]) for row in self.db.execute(total_stmt).all()}

        faltou_stmt = (
            select(Professional.id, func.count(Appointment.id))
            .join(Appointment, Appointment.professional_id == Professional.id)
            .where(
                Appointment.data_hora >= start,
                Appointment.data_hora < end,
                Appointment.status == AppointmentStatus.FALTOU,
            )
            .group_by(Professional.id)
        )
        faltas = {row[0]: row[1] for row in self.db.execute(faltou_stmt).all()}

        result = []
        for prof_id, (nome, total) in totals.items():
            result.append((prof_id, nome, total, faltas.get(prof_id, 0)))
        return result

    def top_patients(self, date_from: date, date_to: date, limit: int) -> list[tuple[int, str, int]]:
        start, end = self._period_bounds(date_from, date_to)
        stmt = (
            select(Patient.id, Patient.nome, func.count(Appointment.id))
            .join(Appointment, Appointment.patient_id == Patient.id)
            .where(Appointment.data_hora >= start, Appointment.data_hora < end)
            .group_by(Patient.id, Patient.nome)
            .order_by(func.count(Appointment.id).desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).all())
