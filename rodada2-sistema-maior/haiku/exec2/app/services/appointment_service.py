from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from app.models import Appointment, WaitingList, Patient, Professional, AvailabilitySchedule
from app.schemas import AppointmentCreate, AppointmentUpdate
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.waiting_list_repository import WaitingListRepository
from app.repositories.professional_repository import ProfessionalRepository
from app.repositories.patient_repository import PatientRepository

class AppointmentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AppointmentRepository(db)
        self.waiting_list_repo = WaitingListRepository(db)
        self.prof_repo = ProfessionalRepository(db)
        self.patient_repo = PatientRepository(db)

    def create_appointment(self, appt_data: AppointmentCreate):
        patient = self.patient_repo.get_by_id(appt_data.patient_id)
        if not patient:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

        professional = self.prof_repo.get_by_id(appt_data.professional_id)
        if not professional:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professional not found")

        if appt_data.appointment_date < datetime.utcnow():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot schedule in the past")

        schedules = self.db.query(AvailabilitySchedule).filter(
            AvailabilitySchedule.professional_id == appt_data.professional_id,
            AvailabilitySchedule.day_of_week == appt_data.appointment_date.weekday()
        ).all()

        if not schedules:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Professional not available on this day")

        time_available = any(
            s.start_time <= appt_data.appointment_date.time() < s.end_time
            for s in schedules
        )
        if not time_available:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Time slot not available")

        conflict = self.repo.get_conflicts(appt_data.professional_id, appt_data.appointment_date)
        if conflict:
            return self._add_to_waiting_list(appt_data.patient_id, conflict.id)

        appointment = Appointment(**appt_data.dict())
        return self.repo.create(appointment)

    def _add_to_waiting_list(self, patient_id: int, appointment_id: int):
        existing = self.db.query(WaitingList).filter(
            WaitingList.appointment_id == appointment_id,
            WaitingList.patient_id == patient_id
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already in waiting list")

        position = self.db.query(WaitingList).filter(
            WaitingList.appointment_id == appointment_id
        ).count() + 1

        waiting_list = WaitingList(
            patient_id=patient_id,
            appointment_id=appointment_id,
            position=position
        )
        return self.waiting_list_repo.create(waiting_list)

    def get_appointment(self, appointment_id: int):
        appointment = self.repo.get_by_id(appointment_id)
        if not appointment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
        return appointment

    def update_appointment(self, appointment_id: int, appt_data: AppointmentUpdate):
        appointment = self.get_appointment(appointment_id)

        for field, value in appt_data.dict(exclude_unset=True).items():
            setattr(appointment, field, value)

        return self.repo.update(appointment)

    def cancel_appointment(self, appointment_id: int, reason: str):
        appointment = self.get_appointment(appointment_id)
        appointment.status = "cancelada"
        appointment.cancellation_reason = reason
        self.repo.update(appointment)

        waiting_list = self.waiting_list_repo.get_first_in_queue(appointment_id)
        if waiting_list:
            waiting_list.notified = True
            self.waiting_list_repo.update(waiting_list)

        return appointment

    def confirm_appointment(self, appointment_id: int):
        appointment = self.get_appointment(appointment_id)
        appointment.status = "confirmada"
        return self.repo.update(appointment)

    def reschedule_appointment(self, appointment_id: int, new_date: datetime):
        appointment = self.get_appointment(appointment_id)

        if new_date < datetime.utcnow():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot reschedule to past")

        conflict = self.repo.get_conflicts(appointment.professional_id, new_date, appointment_id)
        if conflict:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Time slot conflicts")

        appointment.appointment_date = new_date
        return self.repo.update(appointment)

    def get_doctor_agenda(self, professional_id: int, date: datetime):
        self.prof_repo.get_by_id(professional_id)
        return self.repo.get_by_professional_date(professional_id, date)

    def list_patient_appointments(self, patient_id: int, skip: int = 0, limit: int = 100):
        return self.repo.get_by_patient(patient_id, skip, limit)

    def list_appointments_by_status(self, status: str, skip: int = 0, limit: int = 100):
        return self.repo.get_by_status(status, skip, limit)
