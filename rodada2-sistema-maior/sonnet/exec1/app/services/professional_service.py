from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.models.professional import Availability, Professional
from app.models.user import User
from app.models.enums import UserRole
from app.repositories.professional_repository import ProfessionalRepository
from app.repositories.user_repository import UserRepository
from app.schemas.professional import AvailabilityCreate, ProfessionalCreate, ProfessionalUpdate
from app.services.audit_service import AuditService


class ProfessionalService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = ProfessionalRepository(db)
        self.users = UserRepository(db)
        self.audit = AuditService(db)

    def create_professional(
        self, payload: ProfessionalCreate, acting_user_id: int, ip_address: str | None = None
    ) -> Professional:
        if self.users.get_by_email(payload.email):
            raise ConflictError("E-mail já cadastrado.")
        if self.repository.get_by_license_number(payload.license_number):
            raise ConflictError("Número de registro profissional já cadastrado.")

        role = UserRole.DOCTOR if payload.professional_type.value == "medico" else UserRole.NURSE
        user = User(
            email=payload.email.lower(),
            hashed_password=hash_password(payload.password),
            role=role,
        )
        self.db.add(user)
        self.db.flush()

        professional = Professional(
            user_id=user.id,
            full_name=payload.full_name,
            professional_type=payload.professional_type,
            license_number=payload.license_number,
            specialty=payload.specialty,
        )
        self.db.add(professional)
        self.db.commit()
        self.db.refresh(professional)

        self.audit.log(
            acting_user_id, "CREATE_PROFESSIONAL", "Professional", professional.id, ip_address=ip_address
        )
        return professional

    def search_professionals(
        self, specialty: str | None, professional_type: str | None, offset: int, limit: int
    ) -> tuple[list[Professional], int]:
        return self.repository.search(specialty, professional_type, offset, limit)

    def get_professional(self, professional_id: int) -> Professional:
        professional = self.repository.get_by_id(professional_id)
        if professional is None:
            raise NotFoundError("Profissional não encontrado.")
        return professional

    def get_professional_by_user(self, user_id: int) -> Professional:
        professional = self.repository.get_by_user_id(user_id)
        if professional is None:
            raise NotFoundError("Perfil profissional não encontrado.")
        return professional

    def update_professional(
        self,
        professional_id: int,
        payload: ProfessionalUpdate,
        acting_user_id: int,
        ip_address: str | None = None,
    ) -> Professional:
        professional = self.get_professional(professional_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(professional, field, value)
        updated = self.repository.update(professional)
        self.audit.log(
            acting_user_id, "UPDATE_PROFESSIONAL", "Professional", professional_id, ip_address=ip_address
        )
        return updated

    def delete_professional(
        self, professional_id: int, acting_user_id: int, ip_address: str | None = None
    ) -> None:
        professional = self.get_professional(professional_id)
        self.repository.delete(professional)
        self.audit.log(
            acting_user_id, "DELETE_PROFESSIONAL", "Professional", professional_id, ip_address=ip_address
        )

    def add_availability(
        self, professional_id: int, payload: AvailabilityCreate, acting_user_id: int
    ) -> Availability:
        self.get_professional(professional_id)
        availability = Availability(professional_id=professional_id, **payload.model_dump())
        created = self.repository.add_availability(availability)
        self.audit.log(
            acting_user_id, "CREATE_AVAILABILITY", "Availability", created.id
        )
        return created

    def get_availabilities(self, professional_id: int) -> list[Availability]:
        self.get_professional(professional_id)
        return self.repository.get_availabilities(professional_id)
