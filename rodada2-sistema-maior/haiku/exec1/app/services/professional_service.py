from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import NotFoundError, ConflictError, ValidationError, ForbiddenError
from app.core.enums import ProfessionalType, AuditAction
from app.models.professional import Professional
from app.models.user import User
from app.repositories.professional_repository import ProfessionalRepository
from app.services.audit_service import AuditService
from app.utils.validators import validate_crm


class ProfessionalService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = ProfessionalRepository(db)
        self.audit_service = AuditService(db)

    def create(self, professional_data: dict, current_user: User) -> Professional:
        # Validate CRM for doctors
        if professional_data.get("professional_type") == ProfessionalType.DOCTOR:
            if not validate_crm(professional_data.get("license_number", "")):
                raise ValidationError("Invalid CRM format (e.g., 123456/SP)")

        try:
            professional = self.repository.create(professional_data)
            self.audit_service.log(
                action=AuditAction.PROFESSIONAL_CREATED,
                user_id=current_user.id,
                entity_type="Professional",
                entity_id=professional.id
            )
            return professional
        except IntegrityError:
            self.db.rollback()
            raise ConflictError("License number already registered")

    def get(self, professional_id: int) -> Professional:
        professional = self.repository.get(professional_id)
        if not professional:
            raise NotFoundError("Professional not found")
        return professional

    def get_by_user_id(self, user_id: int) -> Professional:
        professional = self.repository.get_by_user_id(user_id)
        if not professional:
            raise NotFoundError("Professional profile not found")
        return professional

    def list(self, pagination=None, filters: dict = None):
        return self.repository.list(filters=filters, pagination=pagination)

    def update(self, professional_id: int, professional_data: dict, current_user: User) -> Professional:
        professional = self.get(professional_id)

        # Check authorization: admin or self
        if current_user.id != professional.user_id and current_user.role.value != "admin":
            raise ForbiddenError("Can only update your own profile")

        # Validate CRM if being updated
        if "license_number" in professional_data and professional_data["license_number"] != professional.license_number:
            if professional.professional_type == ProfessionalType.DOCTOR:
                if not validate_crm(professional_data["license_number"]):
                    raise ValidationError("Invalid CRM format")

        try:
            updated = self.repository.update(professional_id, professional_data)
            self.audit_service.log(
                action=AuditAction.PROFESSIONAL_UPDATED,
                user_id=current_user.id,
                entity_type="Professional",
                entity_id=professional_id
            )
            return updated
        except IntegrityError:
            self.db.rollback()
            raise ConflictError("License number already registered")

    def delete(self, professional_id: int, current_user: User) -> bool:
        professional = self.get(professional_id)
        success = self.repository.delete(professional_id)
        if success:
            self.audit_service.log(
                action=AuditAction.PROFESSIONAL_DELETED,
                user_id=current_user.id,
                entity_type="Professional",
                entity_id=professional_id
            )
        return success
