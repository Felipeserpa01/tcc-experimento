from datetime import datetime, date, time, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    NotFoundError, ConflictError, ValidationError,
    ForbiddenError
)
from app.core.enums import AppointmentStatus, AuditAction, Weekday
from app.models.appointment import Appointment
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.professional_repository import ProfessionalRepository
from app.repositories.availability_repository import AvailabilityRepository
from app.services.audit_service import AuditService
from app.services.waitlist_service import WaitlistService


class AppointmentService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = AppointmentRepository(db)
        self.professional_repo = ProfessionalRepository(db)
        self.availability_repo = AvailabilityRepository(db)
        self.audit_service = AuditService(db)
        self.waitlist_service = WaitlistService(db)

    def create(self, appointment_data: dict, current_user: User) -> Appointment:
        scheduled_date = datetime.fromisoformat(appointment_data["scheduled_date"]).date()
        start_time = datetime.fromisoformat(appointment_data["start_time"]).time()
        end_time = datetime.fromisoformat(appointment_data["end_time"]).time()
        doctor_id = appointment_data["doctor_id"]

        # Validate doctor exists
        doctor = self.professional_repo.get(doctor_id)
        if not doctor:
            raise NotFoundError("Doctor not found")

        # Check if scheduling in past
        appointment_datetime = datetime.combine(scheduled_date, start_time)
        if appointment_datetime < datetime.utcnow():
            raise ValidationError("Cannot schedule appointment in the past")

        # Check for conflicts
        conflict = self.repository.find_conflicting(doctor_id, scheduled_date, start_time, end_time)
        if conflict:
            raise ConflictError("Doctor has a conflicting appointment at this time")

        # Check doctor availability
        weekday = Weekday(scheduled_date.weekday())
        available_slots = self.availability_repo.get_by_professional_and_weekday(doctor_id, weekday)

        if not available_slots:
            raise ValidationError("Doctor is not available on this day")

        slot_available = False
        for slot in available_slots:
            if slot.start_time <= start_time and end_time <= slot.end_time:
                slot_available = True
                break

        if not slot_available:
            raise ValidationError("Requested time is outside doctor's availability")

        # Create appointment
        appointment_data["created_by_user_id"] = current_user.id

        try:
            appointment = self.repository.create(appointment_data)
            self.audit_service.log(
                action=AuditAction.APPOINTMENT_CREATED,
                user_id=current_user.id,
                entity_type="Appointment",
                entity_id=appointment.id
            )
            return appointment
        except IntegrityError:
            self.db.rollback()
            raise ConflictError("Appointment slot is no longer available")

    def get(self, appointment_id: int, current_user: User = None) -> Appointment:
        appointment = self.repository.get(appointment_id)
        if not appointment:
            raise NotFoundError("Appointment not found")

        # Ownership check if patient
        if current_user and current_user.role.value == "patient":
            if appointment.patient.user_id != current_user.id:
                raise ForbiddenError("Cannot access another patient's appointment")

        return appointment

    def confirm(self, appointment_id: int, current_user: User) -> Appointment:
        appointment = self.get(appointment_id, current_user)
        if appointment.status != AppointmentStatus.SCHEDULED:
            raise ValidationError("Only scheduled appointments can be confirmed")

        appointment.status = AppointmentStatus.CONFIRMED
        self.db.add(appointment)
        self.db.commit()

        self.audit_service.log(
            action=AuditAction.APPOINTMENT_CONFIRMED,
            user_id=current_user.id,
            entity_type="Appointment",
            entity_id=appointment_id
        )

        return appointment

    def cancel(self, appointment_id: int, reason: str, current_user: User) -> Appointment:
        appointment = self.get(appointment_id, current_user)
        if appointment.status == AppointmentStatus.CANCELLED:
            raise ValidationError("Appointment is already cancelled")

        appointment.status = AppointmentStatus.CANCELLED
        appointment.cancellation_reason = reason
        self.db.add(appointment)
        self.db.commit()

        self.audit_service.log(
            action=AuditAction.APPOINTMENT_CANCELLED,
            user_id=current_user.id,
            entity_type="Appointment",
            entity_id=appointment_id,
            details={"reason": reason}
        )

        # Check waitlist and notify if slot available
        self.waitlist_service.process_freed_slot(
            appointment.doctor_id,
            appointment.scheduled_date,
            appointment.start_time
        )

        return appointment

    def reschedule(
        self,
        appointment_id: int,
        new_date: date,
        new_start_time: time,
        new_end_time: time,
        current_user: User
    ) -> Appointment:
        appointment = self.get(appointment_id, current_user)

        if appointment.status == AppointmentStatus.CANCELLED:
            raise ValidationError("Cannot reschedule cancelled appointment")

        # Same validation as create
        appointment_datetime = datetime.combine(new_date, new_start_time)
        if appointment_datetime < datetime.utcnow():
            raise ValidationError("Cannot reschedule to past date/time")

        # Check for conflicts (excluding self)
        conflict = self.repository.find_conflicting(
            appointment.doctor_id,
            new_date,
            new_start_time,
            new_end_time,
            exclude_appointment_id=appointment_id
        )
        if conflict:
            raise ConflictError("Doctor has a conflicting appointment at the new time")

        # Check availability
        weekday = Weekday(new_date.weekday())
        available_slots = self.availability_repo.get_by_professional_and_weekday(
            appointment.doctor_id,
            weekday
        )

        if not available_slots:
            raise ValidationError("Doctor is not available on the new date")

        slot_available = False
        for slot in available_slots:
            if slot.start_time <= new_start_time and new_end_time <= slot.end_time:
                slot_available = True
                break

        if not slot_available:
            raise ValidationError("New time is outside doctor's availability")

        appointment.scheduled_date = new_date
        appointment.start_time = new_start_time
        appointment.end_time = new_end_time
        self.db.add(appointment)
        self.db.commit()

        self.audit_service.log(
            action=AuditAction.APPOINTMENT_RESCHEDULED,
            user_id=current_user.id,
            entity_type="Appointment",
            entity_id=appointment_id
        )

        return appointment
