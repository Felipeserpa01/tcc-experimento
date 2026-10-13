"""Rotas de relatorios e indicadores."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.enums import PaymentMethod
from app.models.user import User
from app.schemas.report import (
    AppointmentsReport,
    NoShowReport,
    RevenueReport,
    TopPatientsReport,
)
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Relatorios"])


@router.get(
    "/appointments",
    response_model=AppointmentsReport,
    summary="Consultas por periodo, medico, especialidade e status",
)
def appointments_report(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    professional_id: int | None = Query(None),
    specialty: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AppointmentsReport:
    data = ReportService(db).appointments_report(
        current_user,
        start_date=start_date,
        end_date=end_date,
        professional_id=professional_id,
        specialty=specialty,
    )
    return AppointmentsReport.model_validate(data)


@router.get(
    "/revenue",
    response_model=RevenueReport,
    summary="Faturamento por periodo e forma de pagamento",
)
def revenue_report(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    payment_method: PaymentMethod | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RevenueReport:
    data = ReportService(db).revenue_report(
        current_user,
        start_date=start_date,
        end_date=end_date,
        payment_method=payment_method,
    )
    return RevenueReport.model_validate(data)


@router.get(
    "/no-show", response_model=NoShowReport, summary="Taxa de faltas (no-show) por medico"
)
def no_show_report(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    professional_id: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NoShowReport:
    data = ReportService(db).no_show_report(
        current_user,
        start_date=start_date,
        end_date=end_date,
        professional_id=professional_id,
    )
    return NoShowReport.model_validate(data)


@router.get(
    "/top-patients", response_model=TopPatientsReport, summary="Pacientes mais atendidos"
)
def top_patients_report(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TopPatientsReport:
    data = ReportService(db).top_patients_report(
        current_user, start_date=start_date, end_date=end_date, limit=limit
    )
    return TopPatientsReport.model_validate(data)
