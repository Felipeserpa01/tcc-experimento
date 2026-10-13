"""Professional business logic: CRUD, availability schedule, search by specialty."""
from sqlalchemy.orm import Session

from app.core.enums import ProfessionalType, UserRole
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app.core.security import hash_password
from app.models.professional import AvailabilitySlot, Professional
from app.models.user import User
from app.repositories.professional_repository import ProfessionalRepository
from app.repositories.user_repository import UserRepository
from app.schemas.professional import AvailabilitySlotCreate, ProfessionalCreate, ProfessionalUpdate
from app.services.audit_service import AuditService

TYPE_TO_ROLE = {
    ProfessionalType.MEDICO: UserRole.MEDICO,
    ProfessionalType.ENFERMEIRO: UserRole.ENFERMEIRO,
}


class ProfessionalService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ProfessionalRepository(db)
        self.user_repo = UserRepository(db)
        self.audit = AuditService(db)

    def create(self, data: ProfessionalCreate, actor: User, ip_address: str | None = None) -> Professional:
        if self.user_repo.get_by_email(data.email):
            raise ConflictError("Já existe um usuário cadastrado com este e-mail.")
        if data.crm and self.repo.get_by_crm(data.crm):
            raise ConflictError("Já existe um profissional cadastrado com este CRM.")

        user = User(
            email=data.email.lower(),
            hashed_password=hash_password(data.password),
            role=TYPE_TO_ROLE[data.tipo],
        )
        self.user_repo.create(user)
        self.db.flush()

        professional = Professional(
            user_id=user.id,
            nome=data.nome,
            tipo=data.tipo,
            crm=data.crm,
            especialidade=data.especialidade,
        )
        self.repo.create(professional)
        self.db.commit()
        self.audit.log(actor.id, "PROFESSIONAL_CREATE", "Professional", professional.id, ip_address=ip_address)
        self.db.commit()
        return self.repo.get_by_id(professional.id)

    def get(self, professional_id: int) -> Professional:
        professional = self.repo.get_by_id(professional_id)
        if not professional:
            raise NotFoundError("Profissional não encontrado.")
        return professional

    def update(
        self, professional_id: int, data: ProfessionalUpdate, actor: User, ip_address: str | None = None
    ) -> Professional:
        professional = self.repo.get_by_id(professional_id)
        if not professional:
            raise NotFoundError("Profissional não encontrado.")

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(professional, field, value)

        self.repo.update(professional)
        self.db.commit()
        self.audit.log(actor.id, "PROFESSIONAL_UPDATE", "Professional", professional.id, ip_address=ip_address)
        self.db.commit()
        return self.repo.get_by_id(professional.id)

    def delete(self, professional_id: int, actor: User, ip_address: str | None = None) -> None:
        professional = self.repo.get_by_id(professional_id)
        if not professional:
            raise NotFoundError("Profissional não encontrado.")
        self.repo.delete(professional)
        self.db.commit()
        self.audit.log(actor.id, "PROFESSIONAL_DELETE", "Professional", professional_id, ip_address=ip_address)
        self.db.commit()

    def search(
        self,
        especialidade: str | None,
        tipo: ProfessionalType | None,
        page: int,
        page_size: int,
        sort_by: str | None,
        sort_order: str,
    ) -> tuple[list[Professional], int]:
        return self.repo.search(especialidade, tipo, page, page_size, sort_by, sort_order)

    def _ensure_can_manage_agenda(self, professional: Professional, actor: User) -> None:
        if actor.role == UserRole.ADMIN:
            return
        if actor.role in (UserRole.MEDICO, UserRole.ENFERMEIRO) and professional.user_id == actor.id:
            return
        raise ForbiddenError("Você só pode gerenciar a própria agenda de disponibilidade.")

    def add_availability_slot(
        self, professional_id: int, data: AvailabilitySlotCreate, actor: User, ip_address: str | None = None
    ) -> AvailabilitySlot:
        professional = self.repo.get_by_id(professional_id)
        if not professional:
            raise NotFoundError("Profissional não encontrado.")
        self._ensure_can_manage_agenda(professional, actor)

        for existing in professional.availability_slots:
            if existing.dia_semana == data.dia_semana and data.hora_inicio < existing.hora_fim and data.hora_fim > existing.hora_inicio:
                raise ValidationAppError("Já existe uma faixa de horário sobreposta para este dia.")

        slot = AvailabilitySlot(professional_id=professional_id, **data.model_dump())
        self.repo.add_availability_slot(slot)
        self.db.commit()
        self.audit.log(
            actor.id, "AVAILABILITY_SLOT_CREATE", "Professional", professional_id, ip_address=ip_address
        )
        self.db.commit()
        return slot

    def remove_availability_slot(
        self, professional_id: int, slot_id: int, actor: User, ip_address: str | None = None
    ) -> None:
        professional = self.repo.get_by_id(professional_id)
        if not professional:
            raise NotFoundError("Profissional não encontrado.")
        self._ensure_can_manage_agenda(professional, actor)

        slot = self.repo.get_availability_slot(slot_id)
        if not slot or slot.professional_id != professional_id:
            raise NotFoundError("Faixa de horário não encontrada.")
        self.repo.delete_availability_slot(slot)
        self.db.commit()
        self.audit.log(
            actor.id, "AVAILABILITY_SLOT_DELETE", "Professional", professional_id, ip_address=ip_address
        )
        self.db.commit()
