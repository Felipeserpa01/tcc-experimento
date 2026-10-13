"""Patient business logic and access control."""
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app.models.patient import Patient
from app.models.user import User
from app.repositories.patient_repository import PatientRepository
from app.repositories.user_repository import UserRepository
from app.schemas.patient import PatientCreate, PatientUpdate
from app.services.audit_service import AuditService


class PatientService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PatientRepository(db)
        self.user_repo = UserRepository(db)
        self.audit = AuditService(db)

    def _ensure_can_view(self, patient: Patient, actor: User) -> None:
        if actor.role == UserRole.PACIENTE and patient.user_id != actor.id:
            raise ForbiddenError("Você só pode acessar os seus próprios dados.")

    def create(self, data: PatientCreate, actor: User, ip_address: str | None = None) -> Patient:
        if self.repo.get_by_cpf(data.cpf):
            raise ConflictError("Já existe um paciente cadastrado com este CPF.")

        if data.user_id is not None:
            linked_user = self.user_repo.get_by_id(data.user_id)
            if not linked_user:
                raise NotFoundError("Usuário informado para vínculo não encontrado.")
            if linked_user.role != UserRole.PACIENTE:
                raise ValidationAppError("Só é possível vincular usuários com perfil de paciente.")
            if self.repo.get_by_user_id(data.user_id):
                raise ConflictError("Este usuário já está vinculado a outro cadastro de paciente.")

        patient = Patient(**data.model_dump())
        self.repo.create(patient)
        self.db.commit()
        self.audit.log(actor.id, "PATIENT_CREATE", "Patient", patient.id, ip_address=ip_address)
        self.db.commit()
        return patient

    def get(self, patient_id: int, actor: User) -> Patient:
        patient = self.repo.get_by_id(patient_id)
        if not patient:
            raise NotFoundError("Paciente não encontrado.")
        self._ensure_can_view(patient, actor)
        return patient

    def update(
        self, patient_id: int, data: PatientUpdate, actor: User, ip_address: str | None = None
    ) -> Patient:
        patient = self.repo.get_by_id(patient_id)
        if not patient:
            raise NotFoundError("Paciente não encontrado.")
        self._ensure_can_view(patient, actor)

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(patient, field, value)

        self.repo.update(patient)
        self.db.commit()
        self.audit.log(actor.id, "PATIENT_UPDATE", "Patient", patient.id, ip_address=ip_address)
        self.db.commit()
        return patient

    def delete(self, patient_id: int, actor: User, ip_address: str | None = None) -> None:
        patient = self.repo.get_by_id(patient_id)
        if not patient:
            raise NotFoundError("Paciente não encontrado.")
        self.repo.delete(patient)
        self.db.commit()
        self.audit.log(actor.id, "PATIENT_DELETE", "Patient", patient_id, ip_address=ip_address)
        self.db.commit()

    def search(
        self,
        actor: User,
        nome: str | None,
        cpf: str | None,
        convenio: str | None,
        page: int,
        page_size: int,
        sort_by: str | None,
        sort_order: str,
    ) -> tuple[list[Patient], int]:
        if actor.role == UserRole.PACIENTE:
            raise ForbiddenError("Pacientes não podem listar outros pacientes.")
        return self.repo.search(nome, cpf, convenio, page, page_size, sort_by, sort_order)
