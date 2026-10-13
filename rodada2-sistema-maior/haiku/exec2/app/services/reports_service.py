from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from app.models import Appointment, Charge, Professional, User, AuditLog
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.charge_repository import ChargeRepository

class ReportsService:
    def __init__(self, db: Session):
        self.db = db
        self.appt_repo = AppointmentRepository(db)
        self.charge_repo = ChargeRepository(db)

    def get_appointments_by_period(self, start_date: datetime, end_date: datetime, skip: int = 0, limit: int = 100):
        query = self.db.query(Appointment).filter(
            and_(
                Appointment.appointment_date >= start_date,
                Appointment.appointment_date <= end_date
            )
        )
        return query.offset(skip).limit(limit).all()

    def get_appointments_by_doctor(self, professional_id: int, start_date: datetime = None, end_date: datetime = None):
        query = self.db.query(Appointment).filter(Appointment.professional_id == professional_id)

        if start_date and end_date:
            query = query.filter(
                and_(
                    Appointment.appointment_date >= start_date,
                    Appointment.appointment_date <= end_date
                )
            )

        return query.all()

    def get_appointments_by_specialization(self, specialization: str, start_date: datetime = None, end_date: datetime = None):
        query = self.db.query(Appointment).join(
            Professional, Appointment.professional_id == Professional.id
        ).filter(Professional.specialization.ilike(f"%{specialization}%"))

        if start_date and end_date:
            query = query.filter(
                and_(
                    Appointment.appointment_date >= start_date,
                    Appointment.appointment_date <= end_date
                )
            )

        return query.all()

    def get_appointments_count_by_status(self):
        results = self.db.query(
            Appointment.status,
            func.count(Appointment.id)
        ).group_by(Appointment.status).all()

        return {status: count for status, count in results}

    def get_revenue_by_period(self, start_date: datetime, end_date: datetime):
        total_revenue = self.db.query(func.sum(Charge.amount)).filter(
            and_(
                Charge.status == "pago",
                Charge.created_at >= start_date,
                Charge.created_at <= end_date
            )
        ).scalar() or 0

        discounts = self.db.query(func.sum(Charge.insurance_discount)).filter(
            and_(
                Charge.status == "pago",
                Charge.created_at >= start_date,
                Charge.created_at <= end_date
            )
        ).scalar() or 0

        return {
            "total_revenue": total_revenue,
            "total_discounts": discounts,
            "net_revenue": total_revenue - discounts
        }

    def get_revenue_by_payment_method(self, start_date: datetime, end_date: datetime):
        results = self.db.query(
            Charge.payment_method,
            func.sum(Charge.amount)
        ).filter(
            and_(
                Charge.status == "pago",
                Charge.created_at >= start_date,
                Charge.created_at <= end_date
            )
        ).group_by(Charge.payment_method).all()

        return {method: amount for method, amount in results if method}

    def get_no_show_rate_by_doctor(self, professional_id: int = None):
        query = self.db.query(Professional).join(
            Appointment, Professional.id == Appointment.professional_id
        )

        if professional_id:
            query = query.filter(Professional.id == professional_id)

        results = []
        for prof in query.distinct():
            total = self.db.query(func.count(Appointment.id)).filter(
                Appointment.professional_id == prof.id
            ).scalar()

            no_shows = self.db.query(func.count(Appointment.id)).filter(
                and_(
                    Appointment.professional_id == prof.id,
                    Appointment.status == "faltou"
                )
            ).scalar()

            rate = (no_shows / total * 100) if total > 0 else 0
            results.append({
                "professional_id": prof.id,
                "professional_name": prof.user.full_name,
                "total_appointments": total,
                "no_shows": no_shows,
                "no_show_rate": round(rate, 2)
            })

        return results

    def get_most_attended_patients(self, limit: int = 10):
        results = self.db.query(
            User.id,
            User.full_name,
            func.count(Appointment.id).label("appointment_count")
        ).join(
            Appointment, User.id == Appointment.patient_id
        ).group_by(User.id, User.full_name).order_by(
            func.count(Appointment.id).desc()
        ).limit(limit).all()

        return [
            {
                "patient_id": user_id,
                "patient_name": name,
                "total_appointments": count
            }
            for user_id, name, count in results
        ]

    def get_audit_logs(self, user_id: int = None, action: str = None, skip: int = 0, limit: int = 100):
        query = self.db.query(AuditLog)

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action)

        return query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()
