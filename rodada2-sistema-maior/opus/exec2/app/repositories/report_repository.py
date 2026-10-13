"""Consultas agregadas para relatórios e indicadores."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ColumnElement, case, func, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.models.appointment import Appointment
from app.models.billing import Charge
from app.models.enums import AppointmentStatus, ChargeStatus, PaymentMethod
from app.models.patient import Patient
from app.models.professional import Professional
from app.models.types import Money

_PERIOD_FORMATS = {"day": "%Y-%m-%d", "month": "%Y-%m"}
_ZERO = Decimal("0.00")


def _count_status(status: AppointmentStatus) -> ColumnElement[int]:
    return func.coalesce(func.sum(case((Appointment.status == status, 1), else_=0)), 0)


def _money_sum(column: InstrumentedAttribute[Decimal]) -> ColumnElement[Decimal]:
    return func.coalesce(func.sum(column), 0, type_=Money())


@dataclass(frozen=True)
class ProfessionalCounts:
    professional_id: int
    professional_name: str
    specialty: str | None
    total: int
    completed: int
    cancelled: int
    no_show: int


@dataclass(frozen=True)
class RevenueTotals:
    total: Decimal
    discounts: Decimal
    count: int


class ReportRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------ consultas
    def appointments_by_period(
        self, start: datetime, end: datetime, granularity: str, status: AppointmentStatus | None
    ) -> list[tuple[str, int]]:
        period = func.strftime(_PERIOD_FORMATS[granularity], Appointment.start_at)
        stmt = (
            select(period, func.count(Appointment.id))
            .where(Appointment.start_at >= start, Appointment.start_at < end)
            .group_by(period)
            .order_by(period)
        )
        if status is not None:
            stmt = stmt.where(Appointment.status == status)
        return [(row[0], row[1]) for row in self.db.execute(stmt).all()]

    def appointments_by_professional(
        self, start: datetime, end: datetime, specialty: str | None = None
    ) -> list[ProfessionalCounts]:
        total = func.count(Appointment.id)
        stmt = (
            select(
                Professional.id,
                Professional.full_name,
                Professional.specialty,
                total,
                _count_status(AppointmentStatus.COMPLETED),
                _count_status(AppointmentStatus.CANCELLED),
                _count_status(AppointmentStatus.NO_SHOW),
            )
            .join(Appointment, Appointment.professional_id == Professional.id)
            .where(Appointment.start_at >= start, Appointment.start_at < end)
            .group_by(Professional.id, Professional.full_name, Professional.specialty)
            .order_by(total.desc(), Professional.full_name)
        )
        if specialty:
            stmt = stmt.where(func.lower(Professional.specialty) == specialty.lower())
        return [ProfessionalCounts(*row) for row in self.db.execute(stmt).all()]

    def appointments_by_specialty(self, start: datetime, end: datetime) -> list[tuple[str, int, int]]:
        total = func.count(Appointment.id)
        stmt = (
            select(Professional.specialty, total, _count_status(AppointmentStatus.COMPLETED))
            .join(Appointment, Appointment.professional_id == Professional.id)
            .where(
                Appointment.start_at >= start,
                Appointment.start_at < end,
                Professional.specialty.is_not(None),
            )
            .group_by(Professional.specialty)
            .order_by(total.desc(), Professional.specialty)
        )
        return [(row[0], row[1], row[2]) for row in self.db.execute(stmt).all()]

    def appointments_by_status(
        self, start: datetime, end: datetime, professional_id: int | None = None
    ) -> dict[AppointmentStatus, int]:
        stmt = (
            select(Appointment.status, func.count(Appointment.id))
            .where(Appointment.start_at >= start, Appointment.start_at < end)
            .group_by(Appointment.status)
        )
        if professional_id is not None:
            stmt = stmt.where(Appointment.professional_id == professional_id)
        return {row[0]: row[1] for row in self.db.execute(stmt).all()}

    def top_patients(self, start: datetime, end: datetime, limit: int) -> list[tuple[int, str, int]]:
        total = func.count(Appointment.id)
        stmt = (
            select(Patient.id, Patient.full_name, total)
            .join(Appointment, Appointment.patient_id == Patient.id)
            .where(
                Appointment.status == AppointmentStatus.COMPLETED,
                Appointment.start_at >= start,
                Appointment.start_at < end,
            )
            .group_by(Patient.id, Patient.full_name)
            .order_by(total.desc(), Patient.full_name)
            .limit(limit)
        )
        return [(row[0], row[1], row[2]) for row in self.db.execute(stmt).all()]

    # ------------------------------------------------------------------ faturamento
    def revenue_totals(self, start: datetime, end: datetime) -> RevenueTotals:
        stmt = select(_money_sum(Charge.net_amount), _money_sum(Charge.discount_amount), func.count(Charge.id)).where(
            Charge.status == ChargeStatus.PAID, Charge.paid_at >= start, Charge.paid_at < end
        )
        total, discounts, count = self.db.execute(stmt).one()
        return RevenueTotals(total=total or _ZERO, discounts=discounts or _ZERO, count=count)

    def pending_totals(self, start: datetime, end: datetime) -> tuple[Decimal, int]:
        stmt = select(_money_sum(Charge.net_amount), func.count(Charge.id)).where(
            Charge.status == ChargeStatus.PENDING, Charge.created_at >= start, Charge.created_at < end
        )
        total, count = self.db.execute(stmt).one()
        return total or _ZERO, count

    def revenue_by_payment_method(self, start: datetime, end: datetime) -> list[tuple[PaymentMethod, Decimal, int]]:
        total = _money_sum(Charge.net_amount)
        stmt = (
            select(Charge.payment_method, total, func.count(Charge.id))
            .where(Charge.status == ChargeStatus.PAID, Charge.paid_at >= start, Charge.paid_at < end)
            .group_by(Charge.payment_method)
            .order_by(total.desc())
        )
        return [(row[0], row[1], row[2]) for row in self.db.execute(stmt).all()]

    def revenue_by_period(self, start: datetime, end: datetime, granularity: str) -> list[tuple[str, Decimal, int]]:
        period = func.strftime(_PERIOD_FORMATS[granularity], Charge.paid_at)
        stmt = (
            select(period, _money_sum(Charge.net_amount), func.count(Charge.id))
            .where(Charge.status == ChargeStatus.PAID, Charge.paid_at >= start, Charge.paid_at < end)
            .group_by(period)
            .order_by(period)
        )
        return [(row[0], row[1], row[2]) for row in self.db.execute(stmt).all()]
