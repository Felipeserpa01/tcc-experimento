"""Gestão de pacientes."""

from sqlalchemy.orm import Session

from app.core import clock
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError, PermissionDeniedError
from app.core.pagination import PageParams, PageResult, SortParams
from app.models.enums import Role
from app.models.patient import Patient
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.patient_repository import InsuranceRepository, PatientRepository
from app.schemas.patient import Allergy, PatientBase, PatientCreate, PatientUpdate
from app.services import access
from app.services.audit_service import AuditAction, AuditService

# Campos que cada perfil pode alterar (atualização parcial).
_CLINICAL_FIELDS = frozenset({"allergies", "notes"})
_CONTACT_FIELDS = frozenset({"phone", "email", "address"})
UPDATABLE_FIELDS_BY_ROLE: dict[Role, frozenset[str]] = {
    Role.ADMIN: frozenset(PatientUpdate.model_fields),
    Role.RECEPTIONIST: frozenset(PatientUpdate.model_fields),
    Role.DOCTOR: _CLINICAL_FIELDS,
    Role.NURSE: _CLINICAL_FIELDS,
    Role.PATIENT: _CONTACT_FIELDS,
}


def _serialize_allergies(allergies: list[Allergy]) -> list[dict]:
    return [allergy.model_dump(mode="json") for allergy in allergies]


class PatientService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.patients = PatientRepository(db)
        self.insurances = InsuranceRepository(db)
        self.appointments = AppointmentRepository(db)
        self.audit = AuditService(db)

    # ------------------------------------------------------------------ helpers
    def _ensure_insurance_usable(self, insurance_id: int | None) -> None:
        if insurance_id is None:
            return
        insurance = self.insurances.get(insurance_id)
        if insurance is None:
            raise NotFoundError("Convênio não encontrado.")
        if not insurance.is_active:
            raise BusinessRuleError("O convênio informado está inativo.")

    def build_patient(self, data: PatientBase) -> Patient:
        """Valida unicidade/convênio e monta um paciente (sem persistir)."""
        if self.patients.cpf_exists(data.cpf):
            raise ConflictError("Já existe um paciente cadastrado com este CPF.")
        self._ensure_insurance_usable(data.insurance_id)
        patient = Patient(
            full_name=data.full_name,
            cpf=data.cpf,
            birth_date=data.birth_date,
            sex=data.sex,
            phone=data.phone,
            email=data.email,
            insurance_id=data.insurance_id,
            insurance_card_number=data.insurance_card_number,
            allergies=_serialize_allergies(data.allergies),
            notes=data.notes,
            is_active=True,
        )
        patient.set_address(data.address.model_dump() if data.address else None)
        return patient

    def get(self, actor: User, patient_id: int) -> Patient:
        patient = self.patients.get(patient_id)
        if patient is None:
            raise NotFoundError("Paciente não encontrado.")
        access.ensure_patient_scope(actor, patient.id)
        return patient

    def get_own(self, actor: User) -> Patient:
        if not access.is_patient(actor):
            raise PermissionDeniedError("Disponível apenas para usuários com perfil paciente.")
        return self.get(actor, access.own_patient_id(actor))

    # ------------------------------------------------------------------ CRUD
    def create(self, actor: User, data: PatientCreate) -> Patient:
        patient = self.patients.add(self.build_patient(data))
        self.audit.log(AuditAction.PATIENT_CREATED, actor=actor, entity_type="paciente", entity_id=patient.id)
        self.db.commit()
        return patient

    def search(
        self,
        actor: User,
        page: PageParams,
        sort: SortParams,
        *,
        query: str | None = None,
        name: str | None = None,
        cpf: str | None = None,
        insurance_id: int | None = None,
        insurance_name: str | None = None,
        is_active: bool | None = True,
    ) -> PageResult[Patient]:
        if access.is_patient(actor):
            raise PermissionDeniedError("Pacientes não podem listar outros pacientes. Use /patients/me.")
        return self.patients.search(
            page,
            sort,
            query=query,
            name=name,
            cpf=cpf,
            insurance_id=insurance_id,
            insurance_name=insurance_name,
            is_active=is_active,
        )

    def update(self, actor: User, patient_id: int, data: PatientUpdate) -> Patient:
        patient = self.get(actor, patient_id)
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            raise BusinessRuleError("Nenhum campo informado para atualização.")

        allowed = UPDATABLE_FIELDS_BY_ROLE.get(actor.role, frozenset())
        forbidden = sorted(set(changes) - allowed)
        if forbidden:
            raise PermissionDeniedError(
                "Seu perfil não pode alterar os campos informados.",
                details={"campos_nao_permitidos": forbidden, "campos_permitidos": sorted(allowed)},
            )

        if "cpf" in changes and self.patients.cpf_exists(changes["cpf"], exclude_id=patient.id):
            raise ConflictError("Já existe um paciente cadastrado com este CPF.")
        if changes.get("insurance_id") is not None:
            self._ensure_insurance_usable(changes["insurance_id"])
        if "insurance_id" in changes and changes["insurance_id"] is None:
            changes["insurance_card_number"] = None
        card = changes.get("insurance_card_number", patient.insurance_card_number)
        insurance_id = changes.get("insurance_id", patient.insurance_id)
        if card and insurance_id is None:
            raise BusinessRuleError("Número da carteirinha exige um convênio vinculado.")

        if "address" in changes:
            patient.set_address(changes.pop("address"))
        if "allergies" in changes:
            changes["allergies"] = _serialize_allergies(data.allergies or [])
        for field, value in changes.items():
            setattr(patient, field, value)

        self.audit.log(
            AuditAction.PATIENT_UPDATED,
            actor=actor,
            entity_type="paciente",
            entity_id=patient.id,
            details={"campos": sorted(data.model_fields_set)},
        )
        self.db.commit()
        self.db.refresh(patient)
        return patient

    def deactivate(self, actor: User, patient_id: int) -> None:
        patient = self.get(actor, patient_id)
        if not patient.is_active:
            raise BusinessRuleError("Paciente já está inativo.")
        future = self.appointments.count_future_active(patient_id=patient.id, after=clock.now())
        if future:
            raise ConflictError(
                "Paciente possui consultas futuras ativas. Cancele-as antes de desativar o cadastro.",
                details={"consultas_futuras": future},
            )
        patient.is_active = False
        if patient.user is not None:
            patient.user.is_active = False
            patient.user.token_version += 1
        self.audit.log(AuditAction.PATIENT_DEACTIVATED, actor=actor, entity_type="paciente", entity_id=patient.id)
        self.db.commit()
