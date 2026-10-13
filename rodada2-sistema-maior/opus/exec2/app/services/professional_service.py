"""Gestão de profissionais e da agenda de disponibilidade."""

from datetime import date

from sqlalchemy.orm import Session

from app.core import clock
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.pagination import PageParams, PageResult, SortParams
from app.models.enums import ACTIVE_APPOINTMENT_STATUSES, ProfessionalType
from app.models.professional import Availability, Professional
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.professional_repository import AvailabilityRepository, ProfessionalRepository
from app.schemas.professional import AvailabilityCreate, ProfessionalCreate, ProfessionalUpdate
from app.services import access, scheduling
from app.services.audit_service import AuditAction, AuditService


class ProfessionalService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.professionals = ProfessionalRepository(db)
        self.availabilities = AvailabilityRepository(db)
        self.appointments = AppointmentRepository(db)
        self.audit = AuditService(db)

    # ------------------------------------------------------------------ consulta
    def get(self, professional_id: int) -> Professional:
        professional = self.professionals.get(professional_id)
        if professional is None:
            raise NotFoundError("Profissional não encontrado.")
        return professional

    def get_active_doctor(self, professional_id: int) -> Professional:
        professional = self.get(professional_id)
        if not professional.is_doctor:
            raise BusinessRuleError("Consultas só podem ser agendadas com médicos.")
        if not professional.is_active:
            raise BusinessRuleError("O médico selecionado está inativo.")
        return professional

    def search(
        self,
        page: PageParams,
        sort: SortParams,
        *,
        name: str | None,
        specialty: str | None,
        professional_type: ProfessionalType | None,
        is_active: bool | None,
    ) -> PageResult[Professional]:
        return self.professionals.search(
            page, sort, name=name, specialty=specialty, professional_type=professional_type, is_active=is_active
        )

    def list_specialties(self) -> list[str]:
        return self.professionals.list_specialties()

    # ------------------------------------------------------------------ CRUD
    def _ensure_unique_registration(self, crm: str | None, coren: str | None, exclude_id: int | None = None) -> None:
        if crm and self.professionals.crm_exists(crm, exclude_id=exclude_id):
            raise ConflictError("Já existe um profissional cadastrado com este CRM.")
        if coren and self.professionals.coren_exists(coren, exclude_id=exclude_id):
            raise ConflictError("Já existe um profissional cadastrado com este COREN.")

    def create(self, actor: User, data: ProfessionalCreate) -> Professional:
        self._ensure_unique_registration(data.crm, data.coren)
        professional = self.professionals.add(Professional(**data.model_dump(), is_active=True))
        self.audit.log(
            AuditAction.PROFESSIONAL_CREATED,
            actor=actor,
            entity_type="profissional",
            entity_id=professional.id,
            details={"tipo": data.professional_type.value},
        )
        self.db.commit()
        return professional

    def update(self, actor: User, professional_id: int, data: ProfessionalUpdate) -> Professional:
        professional = self.get(professional_id)
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            raise BusinessRuleError("Nenhum campo informado para atualização.")
        if professional.is_doctor and "coren" in changes:
            raise BusinessRuleError("Médicos não possuem COREN.")
        if not professional.is_doctor and "crm" in changes:
            raise BusinessRuleError("Enfermeiros não possuem CRM.")
        self._ensure_unique_registration(changes.get("crm"), changes.get("coren"), exclude_id=professional.id)
        if changes.get("is_active") is False:
            self._ensure_no_future_appointments(professional)

        for field, value in changes.items():
            setattr(professional, field, value)
        self.audit.log(
            AuditAction.PROFESSIONAL_UPDATED,
            actor=actor,
            entity_type="profissional",
            entity_id=professional.id,
            details={"campos": sorted(changes)},
        )
        self.db.commit()
        return professional

    def deactivate(self, actor: User, professional_id: int) -> None:
        professional = self.get(professional_id)
        if not professional.is_active:
            raise BusinessRuleError("Profissional já está inativo.")
        self._ensure_no_future_appointments(professional)
        professional.is_active = False
        if professional.user is not None:
            professional.user.is_active = False
            professional.user.token_version += 1
        self.audit.log(
            AuditAction.PROFESSIONAL_DEACTIVATED, actor=actor, entity_type="profissional", entity_id=professional.id
        )
        self.db.commit()

    def _ensure_no_future_appointments(self, professional: Professional) -> None:
        future = self.appointments.count_future_active(professional_id=professional.id, after=clock.now())
        if future:
            raise ConflictError(
                "Profissional possui consultas futuras ativas. Cancele ou remarque-as antes de desativá-lo.",
                details={"consultas_futuras": future},
            )

    # ------------------------------------------------------------------ disponibilidade
    def add_availability(self, actor: User, professional_id: int, data: AvailabilityCreate) -> Availability:
        professional = self.get(professional_id)
        access.ensure_own_professional(actor, professional)
        if not professional.is_active:
            raise BusinessRuleError("Não é possível cadastrar agenda para profissional inativo.")

        candidate = Availability(
            professional_id=professional.id,
            weekday=data.weekday,
            start_time=data.start_time,
            end_time=data.end_time,
            slot_minutes=data.slot_minutes,
        )
        for existing in self.availabilities.list_for_weekday(professional.id, data.weekday):
            if scheduling.windows_overlap(existing, candidate):
                raise ConflictError(
                    "A faixa de horário se sobrepõe a outra já cadastrada para este dia.",
                    details={
                        "conflito_com": {
                            "id": existing.id,
                            "inicio": existing.start_time.strftime("%H:%M"),
                            "fim": existing.end_time.strftime("%H:%M"),
                        }
                    },
                )
        self.availabilities.add(candidate)
        self.audit.log(
            AuditAction.AVAILABILITY_CREATED,
            actor=actor,
            entity_type="profissional",
            entity_id=professional.id,
            details={
                "dia_semana": data.weekday,
                "inicio": data.start_time.strftime("%H:%M"),
                "fim": data.end_time.strftime("%H:%M"),
            },
        )
        self.db.commit()
        self.db.refresh(professional)
        return candidate

    def list_availability(self, professional_id: int) -> list[Availability]:
        return list(self.get(professional_id).availabilities)

    def remove_availability(self, actor: User, professional_id: int, availability_id: int) -> None:
        professional = self.get(professional_id)
        access.ensure_own_professional(actor, professional)
        availability = self.availabilities.get(availability_id)
        if availability is None or availability.professional_id != professional.id:
            raise NotFoundError("Faixa de disponibilidade não encontrada para este profissional.")
        self.availabilities.delete(availability)
        self.audit.log(
            AuditAction.AVAILABILITY_DELETED,
            actor=actor,
            entity_type="profissional",
            entity_id=professional.id,
            details={"disponibilidade_id": availability_id},
        )
        self.db.commit()
        self.db.expire(professional, ["availabilities"])

    def available_slots(self, professional_id: int, day: date) -> list[scheduling.Slot]:
        professional = self.get_active_doctor(professional_id)
        now = clock.now()
        if day < now.date():
            raise BusinessRuleError("Não é possível consultar horários de datas passadas.")
        all_slots = scheduling.generate_slots(professional.availabilities, day)
        busy = [
            (appt.start_at, appt.end_at)
            for appt in self.appointments.list_for_professional_on(
                professional.id, day, statuses=ACTIVE_APPOINTMENT_STATUSES
            )
        ]
        return scheduling.free_slots(all_slots, busy, not_before=now)
