from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime
from app.models import Appointment

class AppointmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, appointment_id: int):
        return self.db.query(Appointment).filter(Appointment.id == appointment_id).first()

    def get_by_patient(self, patient_id: int, skip: int = 0, limit: int = 100):
        return self.db.query(Appointment).filter(
            Appointment.patient_id == patient_id
        ).order_by(Appointment.appointment_date.desc()).offset(skip).limit(limit).all()

    def get_by_professional(self, professional_id: int, skip: int = 0, limit: int = 100):
        return self.db.query(Appointment).filter(
            Appointment.professional_id == professional_id
        ).order_by(Appointment.appointment_date.desc()).offset(skip).limit(limit).all()

    def get_by_professional_date(self, professional_id: int, date: datetime):
        return self.db.query(Appointment).filter(
            and_(
                Appointment.professional_id == professional_id,
                Appointment.appointment_date.cast(Date) == date.date()
            )
        ).all()

    def get_conflicts(self, professional_id: int, appointment_date: datetime, appointment_id: int = None):
        query = self.db.query(Appointment).filter(
            and_(
                Appointment.professional_id == professional_id,
                Appointment.appointment_date == appointment_date,
                Appointment.status.in_(["agendada", "confirmada", "em andamento"])
            )
        )
        if appointment_id:
            query = query.filter(Appointment.id != appointment_id)
        return query.first()

    def get_by_status(self, status: str, skip: int = 0, limit: int = 100):
        return self.db.query(Appointment).filter(
            Appointment.status == status
        ).offset(skip).limit(limit).all()

    def get_all(self, skip: int = 0, limit: int = 100):
        return self.db.query(Appointment).offset(skip).limit(limit).all()

    def create(self, appointment: Appointment):
        self.db.add(appointment)
        self.db.commit()
        self.db.refresh(appointment)
        return appointment

    def update(self, appointment: Appointment):
        self.db.commit()
        self.db.refresh(appointment)
        return appointment

    def delete(self, appointment_id: int):
        appointment = self.get_by_id(appointment_id)
        if appointment:
            self.db.delete(appointment)
            self.db.commit()
            return True
        return False

from sqlalchemy import Date
