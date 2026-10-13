from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.enums import UserRole
from app.models.patient import Patient
from app.models.user import User
from app.repositories.patient_repository import PatientRepository
from app.schemas.patient import PatientCreate, PatientUpdate
from app.services.audit_service import AuditService

STAFF_WITH_FULL_PATIENT_ACCESS = {
    UserRole.ADMIN,
    UserRole.DOCTOR,
    UserRole.NURSE,
    UserRole.RECEPTIONIST,
}


class PatientService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = PatientRepository(db)
        self.audit = AuditService(db)

    def create_patient(
        self, payload: PatientCreate, acting_user: User, ip_address: str | None = None
    ) -> Patient:
        if self.repository.get_by_cpf(payload.cpf):
            raise ConflictError("CPF já cadastrado.")

        patient = Patient(**payload.model_dump())
        created = self.repository.create(patient)
        self.audit.log(acting_user.id, "CREATE_PATIENT", "Patient", created.id, ip_address=ip_address)
        return created

    def search_patients(
        self,
        name: str | None,
        cpf: str | None,
        insurance: str | None,
        order_by: str,
        descending: bool,
        offset: int,
        limit: int,
    ) -> tuple[list[Patient], int]:
        return self.repository.search(name, cpf, insurance, order_by, descending, offset, limit)

    def get_patient(self, patient_id: int, acting_user: User) -> Patient:
        patient = self.repository.get_by_id(patient_id)
        if patient is None:
            raise NotFoundError("Paciente não encontrado.")
        self._authorize_access(patient, acting_user)
        return patient

    def get_own_patient_profile(self, acting_user: User) -> Patient:
        patient = self.repository.get_by_user_id(acting_user.id)
        if patient is None:
            raise NotFoundError("Perfil de paciente não encontrado.")
        return patient

    def update_patient(
        self, patient_id: int, payload: PatientUpdate, acting_user: User, ip_address: str | None = None
    ) -> Patient:
        patient = self.get_patient(patient_id, acting_user)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(patient, field, value)
        updated = self.repository.update(patient)
        self.audit.log(acting_user.id, "UPDATE_PATIENT", "Patient", patient_id, ip_address=ip_address)
        return updated

    def delete_patient(self, patient_id: int, acting_user: User, ip_address: str | None = None) -> None:
        patient = self.repository.get_by_id(patient_id)
        if patient is None:
            raise NotFoundError("Paciente não encontrado.")
        self.repository.delete(patient)
        self.audit.log(acting_user.id, "DELETE_PATIENT", "Patient", patient_id, ip_address=ip_address)

    def _authorize_access(self, patient: Patient, acting_user: User) -> None:
        if acting_user.role in STAFF_WITH_FULL_PATIENT_ACCESS:
            return
        if acting_user.role == UserRole.PATIENT and patient.user_id == acting_user.id:
            return
        raise ForbiddenError("Você não tem permissão para acessar os dados deste paciente.")
