"""Relatorios e indicadores (agregacoes feitas no banco)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.datetime_utils import range_bounds
from app.core.exceptions import PermissionDeniedError
from app.models.appointment import Appointment
from app.models.billing import Charge
from app.models.enums import (
    FRONT_DESK_ROLES,
    STAFF_ROLES,
    AppointmentStatus,
    ChargeStatus,
    PaymentMethod,
    UserRole,
)
from app.models.patient import Patient
from app.models.professional import Professional
from app.models.user import User
from app.repositories.professional_repository import ProfessionalRepository
from app.services.audit_service import AuditAction, AuditService


def _percent(part: int, whole: int) -> float:
    return round((part / whole) * 100, 2) if whole else 0.0


class ReportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.professionals = ProfessionalRepository(db)
        self.audit = AuditService(db)

    # ------------------------------------------------------------------
    # Autorizacao
    # ------------------------------------------------------------------
    def _scope_professional(self, actor: User, professional_id: int | None) -> int | None:
        """Medicos so enxergam os proprios indicadores."""
        if actor.role == UserRole.DOCTOR:
            own = self.professionals.get_by_user_id(actor.id)
            if own is None:
                raise PermissionDeniedError("Usuario sem cadastro de profissional vinculado.")
            if professional_id is not None and professional_id != own.id:
                raise PermissionDeniedError("Voce so pode gerar relatorios da sua propria agenda.")
            return own.id
        return professional_id

    @staticmethod
    def ensure_clinical_access(actor: User) -> None:
        if actor.role not in STAFF_ROLES:
            raise PermissionDeniedError("Relatorios sao restritos a equipe da clinica.")

    @staticmethod
    def ensure_financial_access(actor: User) -> None:
        if actor.role not in FRONT_DESK_ROLES:
            raise PermissionDeniedError(
                "Relatorios financeiros sao restritos a administradores e recepcionistas."
            )

    # ------------------------------------------------------------------
    def _appointment_filters(
        self,
        stmt,
        start_date: date | None,
        end_date: date | None,
        professional_id: int | None,
        specialty: str | None,
    ):
        start, end = range_bounds(start_date, end_date)
        if start is not None:
            stmt = stmt.where(Appointment.scheduled_start >= start)
        if end is not None:
            stmt = stmt.where(Appointment.scheduled_start < end)
        if professional_id is not None:
            stmt = stmt.where(Appointment.professional_id == professional_id)
        if specialty:
            stmt = stmt.where(Professional.specialty.ilike(f"%{specialty.strip()}%"))
        return stmt

    # ==================================================================
    # Consultas por periodo / medico / especialidade
    # ==================================================================
    def appointments_report(
        self,
        actor: User,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        professional_id: int | None = None,
        specialty: str | None = None,
    ) -> dict:
        self.ensure_clinical_access(actor)
        professional_id = self._scope_professional(actor, professional_id)

        base = select(Appointment).join(
            Professional, Appointment.professional_id == Professional.id
        )
        base = self._appointment_filters(base, start_date, end_date, professional_id, specialty)
        subquery = base.subquery()
        total = self.db.execute(select(func.count()).select_from(subquery)).scalar_one() or 0

        # Por status
        status_stmt = select(Appointment.status, func.count(Appointment.id)).join(
            Professional, Appointment.professional_id == Professional.id
        )
        status_stmt = self._appointment_filters(
            status_stmt, start_date, end_date, professional_id, specialty
        ).group_by(Appointment.status)
        by_status = [
            {
                "status": status,
                "total": count,
                "percentage": _percent(count, total),
            }
            for status, count in self.db.execute(status_stmt).all()
        ]
        by_status.sort(key=lambda item: item["total"], reverse=True)

        # Por profissional
        professional_stmt = select(
            Professional.id,
            Professional.full_name,
            Professional.specialty,
            func.count(Appointment.id),
        ).join(Professional, Appointment.professional_id == Professional.id)
        professional_stmt = self._appointment_filters(
            professional_stmt, start_date, end_date, professional_id, specialty
        ).group_by(Professional.id, Professional.full_name, Professional.specialty)
        by_professional = [
            {
                "professional_id": pid,
                "professional_name": name,
                "specialty": spec,
                "total": count,
            }
            for pid, name, spec, count in self.db.execute(professional_stmt).all()
        ]
        by_professional.sort(key=lambda item: item["total"], reverse=True)

        # Por especialidade
        specialty_stmt = select(
            func.coalesce(Professional.specialty, "Nao informada"), func.count(Appointment.id)
        ).join(Professional, Appointment.professional_id == Professional.id)
        specialty_stmt = self._appointment_filters(
            specialty_stmt, start_date, end_date, professional_id, specialty
        ).group_by(func.coalesce(Professional.specialty, "Nao informada"))
        by_specialty = [
            {"specialty": spec, "total": count}
            for spec, count in self.db.execute(specialty_stmt).all()
        ]
        by_specialty.sort(key=lambda item: item["total"], reverse=True)

        self.audit.record(
            action=AuditAction.REPORT_GENERATED,
            actor=actor,
            resource_type="report",
            resource_id="appointments",
            description="Relatorio de consultas gerado.",
            extra={"start_date": str(start_date), "end_date": str(end_date)},
        )
        self.db.commit()

        return {
            "period": {"start_date": start_date, "end_date": end_date},
            "total_appointments": total,
            "by_status": by_status,
            "by_professional": by_professional,
            "by_specialty": by_specialty,
        }

    # ==================================================================
    # Faturamento por periodo e forma de pagamento
    # ==================================================================
    def revenue_report(
        self,
        actor: User,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        payment_method: PaymentMethod | None = None,
    ) -> dict:
        self.ensure_financial_access(actor)
        start, end = range_bounds(start_date, end_date)

        def apply_filters(stmt):
            if start is not None:
                stmt = stmt.where(Charge.created_at >= start)
            if end is not None:
                stmt = stmt.where(Charge.created_at < end)
            if payment_method is not None:
                stmt = stmt.where(Charge.payment_method == payment_method)
            return stmt

        totals_stmt = apply_filters(
            select(
                func.coalesce(func.sum(Charge.net_amount), 0),
                func.coalesce(func.sum(Charge.discount_amount), 0),
                func.coalesce(
                    func.sum(
                        case((Charge.status == ChargeStatus.PAID, Charge.paid_amount), else_=0)
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case((Charge.status == ChargeStatus.PENDING, Charge.net_amount), else_=0)
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case((Charge.status == ChargeStatus.CANCELLED, Charge.net_amount), else_=0)
                    ),
                    0,
                ),
            )
        )
        billed, discounts, received, pending, cancelled = self.db.execute(totals_stmt).one()

        method_stmt = apply_filters(
            select(
                Charge.payment_method,
                func.count(Charge.id),
                func.coalesce(func.sum(Charge.paid_amount), 0),
            ).where(Charge.status == ChargeStatus.PAID)
        ).group_by(Charge.payment_method)
        by_payment_method = [
            {
                "payment_method": method,
                "total_charges": count,
                "total_amount": Decimal(str(amount)),
            }
            for method, count, amount in self.db.execute(method_stmt).all()
        ]

        status_stmt = apply_filters(
            select(
                Charge.status,
                func.count(Charge.id),
                func.coalesce(func.sum(Charge.net_amount), 0),
            )
        ).group_by(Charge.status)
        by_status = [
            {"status": status, "total_charges": count, "total_amount": Decimal(str(amount))}
            for status, count, amount in self.db.execute(status_stmt).all()
        ]

        self.audit.record(
            action=AuditAction.REPORT_GENERATED,
            actor=actor,
            resource_type="report",
            resource_id="revenue",
            description="Relatorio de faturamento gerado.",
        )
        self.db.commit()

        return {
            "period": {"start_date": start_date, "end_date": end_date},
            "total_billed": Decimal(str(billed)),
            "total_received": Decimal(str(received)),
            "total_pending": Decimal(str(pending)),
            "total_cancelled": Decimal(str(cancelled)),
            "total_discounts": Decimal(str(discounts)),
            "by_payment_method": by_payment_method,
            "by_status": by_status,
        }

    # ==================================================================
    # Taxa de faltas (no-show)
    # ==================================================================
    def no_show_report(
        self,
        actor: User,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        professional_id: int | None = None,
    ) -> dict:
        self.ensure_clinical_access(actor)
        professional_id = self._scope_professional(actor, professional_id)
        start, end = range_bounds(start_date, end_date)

        no_show_expr = func.sum(
            case((Appointment.status == AppointmentStatus.NO_SHOW, 1), else_=0)
        )
        stmt = (
            select(
                Professional.id,
                Professional.full_name,
                Professional.specialty,
                func.count(Appointment.id),
                no_show_expr,
            )
            .join(Professional, Appointment.professional_id == Professional.id)
            .where(Appointment.status != AppointmentStatus.CANCELLED)
        )
        if start is not None:
            stmt = stmt.where(Appointment.scheduled_start >= start)
        if end is not None:
            stmt = stmt.where(Appointment.scheduled_start < end)
        if professional_id is not None:
            stmt = stmt.where(Appointment.professional_id == professional_id)
        stmt = stmt.group_by(Professional.id, Professional.full_name, Professional.specialty)

        items = []
        overall_total = 0
        overall_no_show = 0
        for pid, name, spec, total, no_shows in self.db.execute(stmt).all():
            total = int(total or 0)
            no_shows = int(no_shows or 0)
            overall_total += total
            overall_no_show += no_shows
            items.append(
                {
                    "professional_id": pid,
                    "professional_name": name,
                    "specialty": spec,
                    "total_appointments": total,
                    "no_show_count": no_shows,
                    "no_show_rate_percent": _percent(no_shows, total),
                }
            )
        items.sort(key=lambda item: item["no_show_rate_percent"], reverse=True)

        self.audit.record(
            action=AuditAction.REPORT_GENERATED,
            actor=actor,
            resource_type="report",
            resource_id="no_show",
            description="Relatorio de taxa de faltas gerado.",
        )
        self.db.commit()

        return {
            "period": {"start_date": start_date, "end_date": end_date},
            "overall_total": overall_total,
            "overall_no_show": overall_no_show,
            "overall_rate_percent": _percent(overall_no_show, overall_total),
            "by_professional": items,
        }

    # ==================================================================
    # Pacientes mais atendidos
    # ==================================================================
    def top_patients_report(
        self,
        actor: User,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 10,
    ) -> dict:
        self.ensure_clinical_access(actor)
        professional_id = self._scope_professional(actor, None)
        start, end = range_bounds(start_date, end_date)

        completed_expr = func.sum(
            case((Appointment.status == AppointmentStatus.COMPLETED, 1), else_=0)
        )
        stmt = (
            select(
                Patient.id,
                Patient.full_name,
                func.count(Appointment.id),
                completed_expr,
                func.max(Appointment.scheduled_start),
            )
            .join(Patient, Appointment.patient_id == Patient.id)
            .where(Appointment.status != AppointmentStatus.CANCELLED)
        )
        if start is not None:
            stmt = stmt.where(Appointment.scheduled_start >= start)
        if end is not None:
            stmt = stmt.where(Appointment.scheduled_start < end)
        if professional_id is not None:
            stmt = stmt.where(Appointment.professional_id == professional_id)
        stmt = (
            stmt.group_by(Patient.id, Patient.full_name)
            .order_by(func.count(Appointment.id).desc(), Patient.full_name.asc())
            .limit(limit)
        )

        items = []
        for pid, name, total, completed, last_at in self.db.execute(stmt).all():
            items.append(
                {
                    "patient_id": pid,
                    "patient_name": name,
                    "total_appointments": int(total or 0),
                    "completed_appointments": int(completed or 0),
                    "last_appointment_at": last_at.date() if last_at else None,
                }
            )

        self.audit.record(
            action=AuditAction.REPORT_GENERATED,
            actor=actor,
            resource_type="report",
            resource_id="top_patients",
            description="Relatorio de pacientes mais atendidos gerado.",
        )
        self.db.commit()

        return {
            "period": {"start_date": start_date, "end_date": end_date},
            "items": items,
        }
