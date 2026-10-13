"""Relatórios gerenciais e indicadores."""

from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.core import clock
from app.core.exceptions import InvalidInputError
from app.models.enums import AppointmentStatus
from app.repositories.report_repository import ReportRepository
from app.schemas.report import (
    AppointmentsByPeriodReport,
    AppointmentsByProfessionalReport,
    AppointmentsBySpecialtyReport,
    AppointmentsByStatusReport,
    NoShowRate,
    NoShowReport,
    PaymentMethodRevenue,
    PeriodCount,
    PeriodRevenue,
    ProfessionalAppointmentCount,
    ReportPeriod,
    RevenueReport,
    SpecialtyCount,
    StatusCount,
    TopPatient,
    TopPatientsReport,
)

MAX_RANGE_DAYS = 366 * 5
DEFAULT_RANGE_DAYS = 30


def _percentage(part: int, whole: int) -> Decimal:
    if whole == 0:
        return Decimal("0.00")
    return (Decimal(part) * 100 / Decimal(whole)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class ReportService:
    def __init__(self, db: Session) -> None:
        self.repo = ReportRepository(db)

    @staticmethod
    def resolve_period(date_from: date | None, date_to: date | None) -> tuple[ReportPeriod, datetime, datetime]:
        """Período padrão: últimos 30 dias. Retorna também os limites [início, fim) em datetime."""
        date_to = date_to or clock.today()
        date_from = date_from or (date_to - timedelta(days=DEFAULT_RANGE_DAYS - 1))
        if date_from > date_to:
            raise InvalidInputError("'date_from' deve ser anterior ou igual a 'date_to'.")
        if (date_to - date_from).days > MAX_RANGE_DAYS:
            raise InvalidInputError(f"O período máximo de um relatório é de {MAX_RANGE_DAYS} dias.")
        start = datetime.combine(date_from, time.min)
        end = datetime.combine(date_to, time.min) + timedelta(days=1)
        return ReportPeriod(date_from=date_from, date_to=date_to), start, end

    def appointments_by_period(
        self, date_from: date | None, date_to: date | None, granularity: str, status: AppointmentStatus | None
    ) -> AppointmentsByPeriodReport:
        period, start, end = self.resolve_period(date_from, date_to)
        rows = self.repo.appointments_by_period(start, end, granularity, status)
        items = [PeriodCount(period=label, total=total) for label, total in rows]
        return AppointmentsByPeriodReport(
            period=period, granularity=granularity, total=sum(i.total for i in items), items=items
        )

    def appointments_by_professional(
        self, date_from: date | None, date_to: date | None, specialty: str | None
    ) -> AppointmentsByProfessionalReport:
        period, start, end = self.resolve_period(date_from, date_to)
        items = [
            ProfessionalAppointmentCount(
                professional_id=row.professional_id,
                professional_name=row.professional_name,
                specialty=row.specialty,
                total=row.total,
                completed=row.completed,
                cancelled=row.cancelled,
                no_show=row.no_show,
            )
            for row in self.repo.appointments_by_professional(start, end, specialty)
        ]
        return AppointmentsByProfessionalReport(period=period, total=sum(i.total for i in items), items=items)

    def appointments_by_specialty(self, date_from: date | None, date_to: date | None) -> AppointmentsBySpecialtyReport:
        period, start, end = self.resolve_period(date_from, date_to)
        items = [
            SpecialtyCount(specialty=specialty, total=total, completed=completed)
            for specialty, total, completed in self.repo.appointments_by_specialty(start, end)
        ]
        return AppointmentsBySpecialtyReport(period=period, total=sum(i.total for i in items), items=items)

    def appointments_by_status(
        self, date_from: date | None, date_to: date | None, professional_id: int | None
    ) -> AppointmentsByStatusReport:
        period, start, end = self.resolve_period(date_from, date_to)
        counts = self.repo.appointments_by_status(start, end, professional_id)
        items = [StatusCount(status=status, total=counts.get(status, 0)) for status in AppointmentStatus]
        return AppointmentsByStatusReport(period=period, total=sum(i.total for i in items), items=items)

    def revenue(self, date_from: date | None, date_to: date | None, granularity: str) -> RevenueReport:
        period, start, end = self.resolve_period(date_from, date_to)
        totals = self.repo.revenue_totals(start, end)
        pending_total, pending_count = self.repo.pending_totals(start, end)
        return RevenueReport(
            period=period,
            granularity=granularity,
            total_received=totals.total,
            total_discounts=totals.discounts,
            paid_count=totals.count,
            pending_total=pending_total,
            pending_count=pending_count,
            by_payment_method=[
                PaymentMethodRevenue(payment_method=method, total=total, count=count)
                for method, total, count in self.repo.revenue_by_payment_method(start, end)
            ],
            by_period=[
                PeriodRevenue(period=label, total=total, count=count)
                for label, total, count in self.repo.revenue_by_period(start, end, granularity)
            ],
        )

    def no_show_rate(self, date_from: date | None, date_to: date | None) -> NoShowReport:
        """Taxa de faltas = faltas / (realizadas + faltas). Cancelamentos não entram no cálculo."""
        period, start, end = self.resolve_period(date_from, date_to)
        items: list[NoShowRate] = []
        total_completed = total_no_show = 0
        for row in self.repo.appointments_by_professional(start, end):
            considered = row.completed + row.no_show
            if considered == 0:
                continue
            total_completed += row.completed
            total_no_show += row.no_show
            items.append(
                NoShowRate(
                    professional_id=row.professional_id,
                    professional_name=row.professional_name,
                    specialty=row.specialty,
                    completed=row.completed,
                    no_show=row.no_show,
                    no_show_rate=_percentage(row.no_show, considered),
                )
            )
        items.sort(key=lambda item: (-item.no_show_rate, item.professional_name))
        return NoShowReport(
            period=period,
            overall_rate=_percentage(total_no_show, total_completed + total_no_show),
            items=items,
        )

    def top_patients(self, date_from: date | None, date_to: date | None, limit: int) -> TopPatientsReport:
        period, start, end = self.resolve_period(date_from, date_to)
        items = [
            TopPatient(patient_id=patient_id, patient_name=name, total_appointments=total)
            for patient_id, name, total in self.repo.top_patients(start, end, limit)
        ]
        return TopPatientsReport(period=period, items=items)
