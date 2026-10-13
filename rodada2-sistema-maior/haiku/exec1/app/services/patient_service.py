from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import NotFoundError, ConflictError, ForbiddenError, ValidationError
from app.core.enums import Role, AuditAction
from app.models.patient import Patient
from app.models.user import User
from app.repositories.patient_repository import PatientRepository
from app.services.audit_service import AuditService
from app.utils.validators import validate_cpf


class PatientService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = PatientRepository(db)
        self.audit_service = AuditService(db)

    def create(self, patient_data: dict, user: User = None) -> Patient:
        # Validate CPF
        if not validate_cpf(patient_data.get("cpf", "")):
            raise ValidationError("Invalid CPF format")

        # Ensure email is unique at user level if creating linked user
        try:
            patient = self.repository.create(patient_data)
            self.audit_service.log(
                action=AuditAction.PATIENT_CREATED,
                user_id=user.id if user else None,
                entity_type="Patient",
                entity_id=patient.id
            )
            return patient
        except IntegrityError:
            self.db.rollback()
            raise ConflictError("CPF already registered")

    def get(self, patient_id: int, current_user: User = None) -> Patient:
        patient = self.repository.get(patient_id)
        if not patient:
            raise NotFoundError("Patient not found")

        # Ownership check: patient can only access their own record
        if current_user and current_user.role == Role.PATIENT:
            if patient.user_id != current_user.id:
                raise ForbiddenError("Cannot access another patient's record")

        return patient

    def list(self, pagination=None, filters: dict = None):
        return self.repository.list(filters=filters, pagination=pagination)

    def update(self, patient_id: int, patient_data: dict, current_user: User) -> Patient:
        patient = self.get(patient_id, current_user)

        # Validate CPF if being updated
        if "cpf" in patient_data and patient_data["cpf"] != patient.cpf:
            if not validate_cpf(patient_data["cpf"]):
                raise ValidationError("Invalid CPF format")

        try:
            updated = self.repository.update(patient_id, patient_data)
            self.audit_service.log(
                action=AuditAction.PATIENT_UPDATED,
                user_id=current_user.id,
                entity_type="Patient",
                entity_id=patient_id
            )
            return updated
        except IntegrityError:
            self.db.rollback()
            raise ConflictError("CPF already registered")

    def delete(self, patient_id: int, current_user: User) -> bool:
        patient = self.get(patient_id, current_user)
        success = self.repository.delete(patient_id)
        if success:
            self.audit_service.log(
                action=AuditAction.PATIENT_DELETED,
                user_id=current_user.id,
                entity_type="Patient",
                entity_id=patient_id
            )
        return success

    def get_by_user_id(self, user_id: int) -> Patient:
        patient = self.repository.get_by_user_id(user_id)
        if not patient:
            raise NotFoundError("Patient profile not found")
        return patient
