"""Regras de negocio de pacientes e convenios."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import (
    BusinessRuleError,
    DuplicateResourceError,
    NotFoundError,
    PermissionDeniedError,
    ValidationFailedError,
)
from app.core.pagination import PaginationParams
from app.core.security import hash_password
from app.models.enums import STAFF_ROLES, UserRole
from app.models.patient import HealthInsurance, Patient
from app.models.user import User
from app.repositories.patient_repository import HealthInsuranceRepository, PatientRepository
from app.repositories.user_repository import UserRepository
from app.schemas.patient import (
    HealthInsuranceCreate,
    HealthInsuranceUpdate,
    PatientCreate,
    PatientUpdate,
)
from app.services.audit_service import AuditAction, AuditService

#: Perfis autorizados a criar/editar/remover cadastros de pacientes.
PATIENT_WRITE_ROLES = frozenset({UserRole.ADMIN, UserRole.RECEPTIONIST})


class HealthInsuranceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = HealthInsuranceRepository(db)
        self.audit = AuditService(db)

    def get(self, insurance_id: int) -> HealthInsurance:
        insurance = self.repository.get(insurance_id)
        if insurance is None:
            raise NotFoundError(f"Convenio {insurance_id} nao encontrado.")
        return insurance

    def search(
        self, pagination: PaginationParams, *, query: str | None = None, is_active: bool | None = None
    ) -> tuple[list[HealthInsurance], int]:
        return self.repository.search(pagination, query=query, is_active=is_active)

    def create(self, payload: HealthInsuranceCreate, actor: User) -> HealthInsurance:
        if self.repository.get_by_name(payload.name):
            raise DuplicateResourceError(f"Ja existe um convenio chamado '{payload.name}'.")
        insurance = HealthInsurance(**payload.model_dump())
        self.db.add(insurance)
        self.db.flush()
        self.audit.record(
            action="insurance.created",
            actor=actor,
            resource_type="health_insurance",
            resource_id=insurance.id,
            description=f"Convenio '{insurance.name}' criado.",
        )
        self.db.commit()
        self.db.refresh(insurance)
        return insurance

    def update(self, insurance_id: int, payload: HealthInsuranceUpdate, actor: User) -> HealthInsurance:
        insurance = self.get(insurance_id)
        data = payload.model_dump(exclude_unset=True)
        if "name" in data and data["name"]:
            existing = self.repository.get_by_name(data["name"])
            if existing and existing.id != insurance.id:
                raise DuplicateResourceError(f"Ja existe um convenio chamado '{data['name']}'.")
        for field, value in data.items():
            setattr(insurance, field, value)
        self.db.flush()
        self.audit.record(
            action="insurance.updated",
            actor=actor,
            resource_type="health_insurance",
            resource_id=insurance.id,
            description=f"Convenio '{insurance.name}' atualizado.",
        )
        self.db.commit()
        self.db.refresh(insurance)
        return insurance


class PatientService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = PatientRepository(db)
        self.users = UserRepository(db)
        self.insurances = HealthInsuranceRepository(db)
        self.audit = AuditService(db)

    # ------------------------------------------------------------------
    # Autorizacao
    # ------------------------------------------------------------------
    @staticmethod
    def ensure_can_write(actor: User) -> None:
        if actor.role not in PATIENT_WRITE_ROLES:
            raise PermissionDeniedError(
                "Apenas administradores e recepcionistas podem manter cadastros de pacientes."
            )

    def ensure_can_read(self, actor: User, patient: Patient) -> None:
        """Paciente so acessa os proprios dados; equipe acessa todos."""
        if actor.role in STAFF_ROLES:
            return
        if actor.role == UserRole.PATIENT and patient.user_id == actor.id:
            return
        raise PermissionDeniedError("Voce so pode acessar os proprios dados.")

    def resolve_own_patient(self, actor: User) -> Patient:
        patient = self.repository.get_by_user_id(actor.id)
        if patient is None:
            raise NotFoundError("Nenhum cadastro de paciente vinculado a este usuario.")
        return patient

    # ------------------------------------------------------------------
    def get(self, patient_id: int, actor: User) -> Patient:
        patient = self.repository.get(patient_id)
        if patient is None:
            raise NotFoundError(f"Paciente {patient_id} nao encontrado.")
        self.ensure_can_read(actor, patient)
        return patient

    def search(
        self,
        pagination: PaginationParams,
        actor: User,
        *,
        query: str | None = None,
        cpf: str | None = None,
        insurance_id: int | None = None,
        insurance_name: str | None = None,
        city: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[Patient], int]:
        if actor.role == UserRole.PATIENT:
            # Um paciente so enxerga o proprio cadastro na listagem.
            own = self.repository.get_by_user_id(actor.id)
            return ([own], 1) if own else ([], 0)

        return self.repository.search(
            pagination,
            query=query,
            cpf=cpf,
            insurance_id=insurance_id,
            insurance_name=insurance_name,
            city=city,
            is_active=is_active,
        )

    # ------------------------------------------------------------------
    def create(self, payload: PatientCreate, actor: User) -> Patient:
        self.ensure_can_write(actor)

        if self.repository.cpf_taken(payload.cpf):
            raise DuplicateResourceError("Ja existe um paciente cadastrado com este CPF.")

        if payload.insurance_id is not None:
            insurance = self.insurances.get(payload.insurance_id)
            if insurance is None:
                raise NotFoundError(f"Convenio {payload.insurance_id} nao encontrado.")
            if not insurance.is_active:
                raise BusinessRuleError(f"O convenio '{insurance.name}' esta inativo.")

        data = payload.model_dump(exclude={"create_user_account", "account_password"})
        patient = Patient(**data)

        if payload.create_user_account:
            if not payload.email:
                raise ValidationFailedError(
                    "Informe o email do paciente para criar o acesso ao portal."
                )
            if not payload.account_password:
                raise ValidationFailedError("Informe `account_password` para criar o acesso.")
            email = payload.email.strip().lower()
            if self.users.email_taken(email):
                raise DuplicateResourceError("Ja existe um usuario com este email.")
            user = User(
                email=email,
                full_name=payload.full_name,
                hashed_password=hash_password(payload.account_password),
                role=UserRole.PATIENT,
                is_active=True,
            )
            self.db.add(user)
            self.db.flush()
            patient.user_id = user.id

        self.db.add(patient)
        self.db.flush()

        self.audit.record(
            action=AuditAction.PATIENT_CREATED,
            actor=actor,
            resource_type="patient",
            resource_id=patient.id,
            description=f"Paciente '{patient.full_name}' cadastrado.",
        )
        self.db.commit()
        self.db.refresh(patient)
        return patient

    def update(self, patient_id: int, payload: PatientUpdate, actor: User) -> Patient:
        patient = self.repository.get(patient_id)
        if patient is None:
            raise NotFoundError(f"Paciente {patient_id} nao encontrado.")

        data = payload.model_dump(exclude_unset=True)
        is_own_record = actor.role == UserRole.PATIENT and patient.user_id == actor.id

        if is_own_record:
            # O proprio paciente so atualiza dados de contato.
            allowed = {
                "phone",
                "email",
                "address_street",
                "address_number",
                "address_complement",
                "address_district",
                "address_city",
                "address_state",
                "address_zip_code",
            }
            forbidden = sorted(set(data) - allowed)
            if forbidden:
                raise PermissionDeniedError(
                    "Voce so pode atualizar seus dados de contato e endereco.",
                    details={"forbidden_fields": forbidden},
                )
        else:
            self.ensure_can_write(actor)

        if "insurance_id" in data and data["insurance_id"] is not None:
            insurance = self.insurances.get(data["insurance_id"])
            if insurance is None:
                raise NotFoundError(f"Convenio {data['insurance_id']} nao encontrado.")
            if not insurance.is_active:
                raise BusinessRuleError(f"O convenio '{insurance.name}' esta inativo.")

        for field, value in data.items():
            setattr(patient, field, value)
        self.db.flush()

        self.audit.record(
            action=AuditAction.PATIENT_UPDATED,
            actor=actor,
            resource_type="patient",
            resource_id=patient.id,
            description=f"Cadastro do paciente '{patient.full_name}' atualizado.",
            extra={"fields": sorted(data.keys())},
        )
        self.db.commit()
        self.db.refresh(patient)
        return patient

    def deactivate(self, patient_id: int, actor: User) -> Patient:
        """Exclusao logica: o historico clinico precisa ser preservado."""
        if actor.role != UserRole.ADMIN:
            raise PermissionDeniedError("Apenas administradores podem remover pacientes.")

        patient = self.repository.get(patient_id)
        if patient is None:
            raise NotFoundError(f"Paciente {patient_id} nao encontrado.")
        if not patient.is_active:
            raise BusinessRuleError("Paciente ja esta inativo.")

        patient.is_active = False
        if patient.user is not None:
            patient.user.is_active = False
        self.db.flush()

        self.audit.record(
            action=AuditAction.PATIENT_DELETED,
            actor=actor,
            resource_type="patient",
            resource_id=patient.id,
            description=f"Paciente '{patient.full_name}' desativado (exclusao logica).",
        )
        self.db.commit()
        self.db.refresh(patient)
        return patient
