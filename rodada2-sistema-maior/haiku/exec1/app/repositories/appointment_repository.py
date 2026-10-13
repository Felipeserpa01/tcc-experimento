from datetime import date, time
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.appointment import Appointment
from app.core.enums import AppointmentStatus
from .base_repository import BaseRepository


class AppointmentRepository(BaseRepository[Appointment]):
    def __init__(self, db: Session):
        super().__init__(db, Appointment)

    def find_conflicting(
        self,
        doctor_id: int,
        scheduled_date: date,
        start_time: time,
        end_time: time,
        exclude_appointment_id: int = None
    ) -> Appointment | None:
        """Find if there's a conflicting appointment for the doctor at this time."""
        query = self.db.query(Appointment).filter(
            Appointment.doctor_id == doctor_id,
            Appointment.scheduled_date == scheduled_date,
            Appointment.status.notin_([AppointmentStatus.CANCELLED]),
            and_(
                Appointment.start_time < end_time,
                Appointment.end_time > start_time
            )
        )

        if exclude_appointment_id:
            query = query.filter(Appointment.id != exclude_appointment_id)

        return query.first()

    def get_doctor_appointments_by_date(self, doctor_id: int, date_val: date):
        """Get all appointments for a doctor on a specific date."""
        return self.db.query(Appointment).filter(
            Appointment.doctor_id == doctor_id,
            Appointment.scheduled_date == date_val,
            Appointment.status.notin_([AppointmentStatus.CANCELLED])
        ).order_by(Appointment.start_time).all()

    def get_patient_appointments(self, patient_id: int):
        """Get all non-cancelled appointments for a patient."""
        return self.db.query(Appointment).filter(
            Appointment.patient_id == patient_id,
            Appointment.status.notin_([AppointmentStatus.CANCELLED])
        ).order_by(Appointment.scheduled_date, Appointment.start_time).all()
