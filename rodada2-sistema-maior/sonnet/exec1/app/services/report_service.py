from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.billing import Billing
from app.models.enums import AppointmentStatus, BillingStatus
from app.models.patient import Patient
from app.models.professional import Professional


class ReportService:
    def __init__(self, db: Session):
        self.db = db

    def appointments_report(
        self,
        start: date | None,
        end: date | None,
        doctor_id: int | None,
        specialty: str | None,
    ) -> list[dict]:
        stmt = select(Appointment).join(Professional, Appointment.doctor_id == Professional.id)
        if start:
            stmt = stmt.where(Appointment.scheduled_at >= datetime.combine(start, datetime.min.time()))
        if end:
            stmt = stmt.where(Appointment.scheduled_at <= datetime.combine(end, datetime.max.time()))
        if doctor_id:
            stmt = stmt.where(Appointment.doctor_id == doctor_id)
        if specialty:
            stmt = stmt.where(Professional.specialty.ilike(f"%{specialty}%"))

        appointments = self.db.execute(stmt).scalars().all()
        return [
            {
                "id": appt.id,
                "patient_name": appt.patient.full_name,
                "doctor_name": appt.doctor.full_name,
                "specialty": appt.doctor.specialty,
                "scheduled_at": appt.scheduled_at,
                "status": appt.status.value,
            }
            for appt in appointments
        ]

    def status_summary(self, start: date | None, end: date | None) -> list[dict]:
        stmt = select(Appointment.status, func.count(Appointment.id)).group_by(Appointment.status)
        if start:
            stmt = stmt.where(Appointment.scheduled_at >= datetime.combine(start, datetime.min.time()))
        if end:
            stmt = stmt.where(Appointment.scheduled_at <= datetime.combine(end, datetime.max.time()))

        rows = self.db.execute(stmt).all()
        return [{"status": status.value, "count": count} for status, count in rows]

    def billing_report(self, start: date, end: date) -> dict:
        stmt = select(Billing).where(
            Billing.created_at >= datetime.combine(start, datetime.min.time()),
            Billing.created_at <= datetime.combine(end, datetime.max.time()),
        )
        billings = self.db.execute(stmt).scalars().all()

        total_amount = sum((b.amount for b in billings), Decimal("0"))
        total_discount = sum((b.discount for b in billings), Decimal("0"))
        total_final = sum((b.final_amount for b in billings), Decimal("0"))

        by_method: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        by_status: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for billing in billings:
            by_method[billing.payment_method.value] += billing.final_amount
            by_status[billing.status.value] += billing.final_amount

        return {
            "period_start": start,
            "period_end": end,
            "total_amount": total_amount,
            "total_discount": total_discount,
            "total_final_amount": total_final,
            "by_payment_method": dict(by_method),
            "by_status": dict(by_status),
        }

    def no_show_rate(self, doctor_id: int | None = None) -> list[dict]:
        stmt = select(Professional)
        if doctor_id:
            stmt = stmt.where(Professional.id == doctor_id)
        professionals = self.db.execute(stmt).scalars().all()

        results = []
        for professional in professionals:
            total_stmt = select(func.count(Appointment.id)).where(
                Appointment.doctor_id == professional.id
            )
            total = self.db.execute(total_stmt).scalar_one()

            no_show_stmt = select(func.count(Appointment.id)).where(
                Appointment.doctor_id == professional.id,
                Appointment.status == AppointmentStatus.NO_SHOW,
            )
            no_show = self.db.execute(no_show_stmt).scalar_one()

            rate = (no_show / total * 100) if total > 0 else 0.0
            results.append(
                {
                    "doctor_id": professional.id,
                    "doctor_name": professional.full_name,
                    "total_appointments": total,
                    "no_show_count": no_show,
                    "no_show_rate": round(rate, 2),
                }
            )
        return results

    def top_patients(self, limit: int = 10) -> list[dict]:
        stmt = (
            select(Patient.id, Patient.full_name, func.count(Appointment.id).label("appointment_count"))
            .join(Appointment, Appointment.patient_id == Patient.id)
            .group_by(Patient.id, Patient.full_name)
            .order_by(func.count(Appointment.id).desc())
            .limit(limit)
        )
        rows = self.db.execute(stmt).all()
        return [
            {"patient_id": pid, "patient_name": name, "appointment_count": count}
            for pid, name, count in rows
        ]
