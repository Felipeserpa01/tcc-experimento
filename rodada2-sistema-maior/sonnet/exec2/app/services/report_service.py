"""Report and indicator aggregation service."""
from datetime import date

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationAppError
from app.repositories.billing_repository import BillingRepository
from app.repositories.report_repository import ReportRepository


class ReportService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ReportRepository(db)
        self.billing_repo = BillingRepository(db)

    @staticmethod
    def _validate_period(date_from: date, date_to: date) -> None:
        if date_from > date_to:
            raise ValidationAppError("Data inicial não pode ser posterior à data final.")

    def appointments_by_period(self, date_from: date, date_to: date) -> list[dict]:
        self._validate_period(date_from, date_to)
        return [{"data": d, "total": t} for d, t in self.repo.appointments_by_period(date_from, date_to)]

    def appointments_by_professional(self, date_from: date, date_to: date) -> list[dict]:
        self._validate_period(date_from, date_to)
        return [
            {"professional_id": pid, "professional_nome": nome, "total": total}
            for pid, nome, total in self.repo.appointments_by_professional(date_from, date_to)
        ]

    def appointments_by_specialty(self, date_from: date, date_to: date) -> list[dict]:
        self._validate_period(date_from, date_to)
        return [
            {"especialidade": esp or "Não informada", "total": total}
            for esp, total in self.repo.appointments_by_specialty(date_from, date_to)
        ]

    def appointments_by_status(self, date_from: date, date_to: date) -> list[dict]:
        self._validate_period(date_from, date_to)
        return [
            {"status": status.value, "total": total}
            for status, total in self.repo.appointments_by_status(date_from, date_to)
        ]

    def revenue_by_period(self, date_from: date, date_to: date) -> list[dict]:
        self._validate_period(date_from, date_to)
        return [{"data": d, "total": total} for d, total in self.billing_repo.revenue_by_period(date_from, date_to)]

    def revenue_by_payment_method(self, date_from: date, date_to: date) -> list[dict]:
        self._validate_period(date_from, date_to)
        return [
            {"forma_pagamento": method.value, "total": total}
            for method, total in self.billing_repo.revenue_by_payment_method(date_from, date_to)
        ]

    def no_show_rate(self, date_from: date, date_to: date) -> list[dict]:
        self._validate_period(date_from, date_to)
        results = []
        for prof_id, nome, total, faltas in self.repo.no_show_rate_by_professional(date_from, date_to):
            taxa = (faltas / total * 100) if total else 0.0
            results.append(
                {
                    "professional_id": prof_id,
                    "professional_nome": nome,
                    "total_consultas": total,
                    "total_faltas": faltas,
                    "taxa_faltas": round(taxa, 2),
                }
            )
        return results

    def top_patients(self, date_from: date, date_to: date, limit: int = 10) -> list[dict]:
        self._validate_period(date_from, date_to)
        return [
            {"patient_id": pid, "patient_nome": nome, "total_consultas": total}
            for pid, nome, total in self.repo.top_patients(date_from, date_to, limit)
        ]
