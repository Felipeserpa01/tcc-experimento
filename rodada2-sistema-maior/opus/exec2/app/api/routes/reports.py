from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import ERROR_RESPONSES, get_report_service, require
from app.core.permissions import Permission
from app.models.enums import AppointmentStatus
from app.schemas.report import (
    AppointmentsByPeriodReport,
    AppointmentsByProfessionalReport,
    AppointmentsBySpecialtyReport,
    AppointmentsByStatusReport,
    NoShowReport,
    RevenueReport,
    TopPatientsReport,
)
from app.services.report_service import ReportService

router = APIRouter(
    prefix="/reports",
    tags=["Relatórios"],
    responses=ERROR_RESPONSES,
    dependencies=[Depends(require(Permission.REPORTS_READ))],
)

Reports = Annotated[ReportService, Depends(get_report_service)]
DateFrom = Annotated[date | None, Query(description="Início do período (padrão: 30 dias atrás)")]
DateTo = Annotated[date | None, Query(description="Fim do período, inclusivo (padrão: hoje)")]
Granularity = Annotated[Literal["day", "month"], Query(description="Agrupamento temporal")]


@router.get("/appointments/by-period", response_model=AppointmentsByPeriodReport, summary="Consultas por período")
def appointments_by_period(
    service: Reports,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    granularity: Granularity = "day",
    status_filter: Annotated[AppointmentStatus | None, Query(alias="status")] = None,
) -> AppointmentsByPeriodReport:
    return service.appointments_by_period(date_from, date_to, granularity, status_filter)


@router.get(
    "/appointments/by-professional",
    response_model=AppointmentsByProfessionalReport,
    summary="Consultas por médico",
)
def appointments_by_professional(
    service: Reports,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    specialty: Annotated[str | None, Query(min_length=2, max_length=100)] = None,
) -> AppointmentsByProfessionalReport:
    return service.appointments_by_professional(date_from, date_to, specialty)


@router.get(
    "/appointments/by-specialty", response_model=AppointmentsBySpecialtyReport, summary="Consultas por especialidade"
)
def appointments_by_specialty(
    service: Reports, date_from: DateFrom = None, date_to: DateTo = None
) -> AppointmentsBySpecialtyReport:
    return service.appointments_by_specialty(date_from, date_to)


@router.get(
    "/appointments/by-status", response_model=AppointmentsByStatusReport, summary="Total de consultas por status"
)
def appointments_by_status(
    service: Reports,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    professional_id: Annotated[int | None, Query(gt=0)] = None,
) -> AppointmentsByStatusReport:
    return service.appointments_by_status(date_from, date_to, professional_id)


@router.get("/revenue", response_model=RevenueReport, summary="Faturamento por período e forma de pagamento")
def revenue(
    service: Reports, date_from: DateFrom = None, date_to: DateTo = None, granularity: Granularity = "day"
) -> RevenueReport:
    return service.revenue(date_from, date_to, granularity)


@router.get("/no-show-rate", response_model=NoShowReport, summary="Taxa de faltas (no-show) por médico")
def no_show_rate(service: Reports, date_from: DateFrom = None, date_to: DateTo = None) -> NoShowReport:
    return service.no_show_rate(date_from, date_to)


@router.get("/top-patients", response_model=TopPatientsReport, summary="Pacientes mais atendidos")
def top_patients(
    service: Reports,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> TopPatientsReport:
    return service.top_patients(date_from, date_to, limit)
