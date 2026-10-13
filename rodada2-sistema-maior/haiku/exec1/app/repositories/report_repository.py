from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.appointment import Appointment
from app.models.billing import Charge
from app.core.enums import AppointmentStatus


class ReportRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_appointments_by_period(self, start_date: date, end_date: date):
        return self.db.query(Appointment).filter(
            Appointment.scheduled_date >= start_date,
            Appointment.scheduled_date <= end_date
        ).all()

    def get_no_show_count_by_doctor(self, doctor_id: int = None):
        query = self.db.query(
            Appointment.doctor_id,
            func.count(Appointment.id).label("total"),
            func.sum(
                func.cast(
                    Appointment.status == AppointmentStatus.NO_SHOW,
                    int
                )
            ).label("no_show_count")
        )

        if doctor_id:
            query = query.filter(Appointment.doctor_id == doctor_id)

        return query.group_by(Appointment.doctor_id).all()

    def get_appointments_by_status(self, start_date: date = None, end_date: date = None):
        query = self.db.query(
            Appointment.status,
            func.count(Appointment.id).label("count")
        )

        if start_date and end_date:
            query = query.filter(
                Appointment.scheduled_date >= start_date,
                Appointment.scheduled_date <= end_date
            )

        return query.group_by(Appointment.status).all()

    def get_revenue_by_period(self, start_date: date, end_date: date):
        return self.db.query(
            func.sum(Charge.final_amount).label("total_revenue"),
            func.count(Charge.id).label("charge_count")
        ).filter(
            Charge.created_at >= start_date,
            Charge.created_at <= end_date,
            Charge.status == "paid"
        ).first()

    def get_most_seen_patients(self, limit: int = 10):
        from app.models.patient import Patient
        return self.db.query(
            Patient,
            func.count(Appointment.id).label("appointment_count")
        ).join(Appointment, Patient.id == Appointment.patient_id).group_by(
            Patient.id
        ).order_by(func.count(Appointment.id).desc()).limit(limit).all()
