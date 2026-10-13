from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ForbiddenError, ConflictError
from app.core.enums import AuditAction
from app.models.medical_record import MedicalRecord
from app.models.user import User
from app.models.appointment import Appointment
from app.repositories.medical_record_repository import MedicalRecordRepository
from app.repositories.appointment_repository import AppointmentRepository
from app.services.audit_service import AuditService


class MedicalRecordService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = MedicalRecordRepository(db)
        self.appointment_repo = AppointmentRepository(db)
        self.audit_service = AuditService(db)

    def create(self, appointment_id: int, record_data: dict, current_user: User) -> MedicalRecord:
        # Verify appointment exists and doctor is assigned
        appointment = self.appointment_repo.get(appointment_id)
        if not appointment:
            raise NotFoundError("Appointment not found")

        # Verify current user is the assigned doctor
        if appointment.doctor_id != current_user.id:
            raise ForbiddenError("Only the assigned doctor can create medical records")

        # Check if record already exists
        existing = self.repository.get_by_appointment_id(appointment_id)
        if existing:
            raise ConflictError("Medical record already exists for this appointment")

        record_data["appointment_id"] = appointment_id
        record = self.repository.create(record_data)

        self.audit_service.log(
            action=AuditAction.MEDICAL_RECORD_CREATED,
            user_id=current_user.id,
            entity_type="MedicalRecord",
            entity_id=record.id
        )

        return record

    def get(self, record_id: int, current_user: User = None) -> MedicalRecord:
        record = self.repository.get(record_id)
        if not record:
            raise NotFoundError("Medical record not found")

        # Ownership check for patients
        if current_user and current_user.role.value == "patient":
            if record.appointment.patient.user_id != current_user.id:
                raise ForbiddenError("Cannot access another patient's medical record")

        return record

    def update(self, record_id: int, record_data: dict, current_user: User) -> MedicalRecord:
        record = self.get(record_id, current_user)

        # Only assigned doctor can update
        if record.appointment.doctor_id != current_user.id:
            raise ForbiddenError("Only the assigned doctor can update this record")

        updated = self.repository.update(record_id, record_data)

        self.audit_service.log(
            action=AuditAction.MEDICAL_RECORD_UPDATED,
            user_id=current_user.id,
            entity_type="MedicalRecord",
            entity_id=record_id
        )

        return updated
