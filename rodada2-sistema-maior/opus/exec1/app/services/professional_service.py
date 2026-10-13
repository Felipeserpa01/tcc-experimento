"""Regras de negocio de profissionais e agenda de disponibilidade."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.datetime_utils import combine, now
from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    DuplicateResourceError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.pagination import PaginationParams
from app.core.security import hash_password
from app.models.enums import CouncilType, ProfessionalType, UserRole
from app.models.professional import Professional, ProfessionalSchedule
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.professional_repository import ProfessionalRepository, ScheduleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.professional import (
    ProfessionalCreate,
    ProfessionalUpdate,
    ScheduleCreate,
    ScheduleUpdate,
)
from app.services.audit_service import AuditAction, AuditService


class ProfessionalService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = ProfessionalRepository(db)
        self.schedules = ScheduleRepository(db)
        self.appointments = AppointmentRepository(db)
        self.users = UserRepository(db)
        self.audit = AuditService(db)

    # ------------------------------------------------------------------
    # Autorizacao
    # ------------------------------------------------------------------
    @staticmethod
    def ensure_admin(actor: User) -> None:
        if actor.role != UserRole.ADMIN:
            raise PermissionDeniedError("Apenas administradores mantem o cadastro de profissionais.")

    def ensure_can_manage_schedule(self, actor: User, professional: Professional) -> None:
        """Admin gerencia qualquer agenda; o profissional gerencia a propria."""
        if actor.role == UserRole.ADMIN:
            return
        if professional.user_id and professional.user_id == actor.id:
            return
        raise PermissionDeniedError("Voce so pode gerenciar a sua propria agenda.")

    # ------------------------------------------------------------------
    def get(self, professional_id: int) -> Professional:
        professional = self.repository.get(professional_id)
        if professional is None:
            raise NotFoundError(f"Profissional {professional_id} nao encontrado.")
        return professional

    def get_doctor(self, professional_id: int) -> Professional:
        professional = self.get(professional_id)
        if not professional.is_doctor:
            raise BusinessRuleError(
                f"O profissional '{professional.full_name}' nao e medico; "
                "consultas so podem ser agendadas com medicos."
            )
        return professional

    def resolve_own_profile(self, actor: User) -> Professional:
        professional = self.repository.get_by_user_id(actor.id)
        if professional is None:
            raise NotFoundError("Nenhum cadastro de profissional vinculado a este usuario.")
        return professional

    def search(
        self,
        pagination: PaginationParams,
        *,
        query: str | None = None,
        specialty: str | None = None,
        professional_type: ProfessionalType | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[Professional], int]:
        return self.repository.search(
            pagination,
            query=query,
            specialty=specialty,
            professional_type=professional_type,
            is_active=is_active,
        )

    def list_specialties(self) -> list[str]:
        return self.repository.list_specialties()

    # ------------------------------------------------------------------
    def create(self, payload: ProfessionalCreate, actor: User) -> Professional:
        self.ensure_admin(actor)

        council_type = payload.council_type or (
            CouncilType.CRM
            if payload.professional_type == ProfessionalType.DOCTOR
            else CouncilType.COREN
        )
        if self.repository.council_taken(council_type, payload.council_number, payload.council_state):
            raise DuplicateResourceError(
                f"Ja existe um profissional com {council_type.value}/"
                f"{payload.council_state} {payload.council_number}."
            )

        professional = Professional(
            full_name=payload.full_name,
            professional_type=payload.professional_type,
            council_type=council_type,
            council_number=payload.council_number,
            council_state=payload.council_state,
            specialty=payload.specialty,
            phone=payload.phone,
            email=payload.email,
            appointment_price=payload.appointment_price,
            appointment_duration_minutes=payload.appointment_duration_minutes,
            is_active=payload.is_active,
        )

        if payload.create_user_account:
            email = (payload.account_email or payload.email or "").strip().lower()
            if self.users.email_taken(email):
                raise DuplicateResourceError("Ja existe um usuario com este email.")
            role = (
                UserRole.DOCTOR
                if payload.professional_type == ProfessionalType.DOCTOR
                else UserRole.NURSE
            )
            user = User(
                email=email,
                full_name=payload.full_name,
                hashed_password=hash_password(payload.account_password),
                role=role,
                is_active=True,
            )
            self.db.add(user)
            self.db.flush()
            professional.user_id = user.id

        self.db.add(professional)
        self.db.flush()

        for schedule_payload in payload.schedules:
            self._add_schedule(professional, schedule_payload)

        self.audit.record(
            action=AuditAction.PROFESSIONAL_CREATED,
            actor=actor,
            resource_type="professional",
            resource_id=professional.id,
            description=(
                f"Profissional '{professional.full_name}' "
                f"({professional.council_label}) cadastrado."
            ),
        )
        self.db.commit()
        self.db.refresh(professional)
        return professional

    def update(self, professional_id: int, payload: ProfessionalUpdate, actor: User) -> Professional:
        professional = self.get(professional_id)
        if actor.role != UserRole.ADMIN and professional.user_id != actor.id:
            raise PermissionDeniedError("Voce so pode atualizar o proprio cadastro.")

        data = payload.model_dump(exclude_unset=True)

        if actor.role != UserRole.ADMIN:
            restricted = {"council_number", "council_state", "appointment_price", "is_active"}
            forbidden = sorted(set(data) & restricted)
            if forbidden:
                raise PermissionDeniedError(
                    "Alteracao restrita ao administrador.",
                    details={"forbidden_fields": forbidden},
                )

        new_number = data.get("council_number", professional.council_number)
        new_state = data.get("council_state", professional.council_state)
        if (new_number, new_state) != (professional.council_number, professional.council_state):
            if self.repository.council_taken(
                professional.council_type, new_number, new_state, exclude_id=professional.id
            ):
                raise DuplicateResourceError("Ja existe outro profissional com este registro.")

        if professional.is_doctor and data.get("specialty") == "":
            raise BusinessRuleError("Medico deve ter especialidade.")

        for field, value in data.items():
            setattr(professional, field, value)
        self.db.flush()

        self.audit.record(
            action=AuditAction.PROFESSIONAL_UPDATED,
            actor=actor,
            resource_type="professional",
            resource_id=professional.id,
            description=f"Profissional '{professional.full_name}' atualizado.",
            extra={"fields": sorted(data.keys())},
        )
        self.db.commit()
        self.db.refresh(professional)
        return professional

    def deactivate(self, professional_id: int, actor: User) -> Professional:
        self.ensure_admin(actor)
        professional = self.get(professional_id)
        if not professional.is_active:
            raise BusinessRuleError("Profissional ja esta inativo.")

        pending = self.appointments.find_conflicts(
            professional.id, now(), now() + timedelta(days=365 * 5)
        )
        if pending:
            raise ConflictError(
                "Nao e possivel desativar: existem consultas futuras ativas para este profissional.",
                details={"active_appointments": len(pending)},
            )

        professional.is_active = False
        if professional.user is not None:
            professional.user.is_active = False
        self.db.flush()

        self.audit.record(
            action=AuditAction.PROFESSIONAL_DELETED,
            actor=actor,
            resource_type="professional",
            resource_id=professional.id,
            description=f"Profissional '{professional.full_name}' desativado.",
        )
        self.db.commit()
        self.db.refresh(professional)
        return professional

    # ------------------------------------------------------------------
    # Agenda de disponibilidade
    # ------------------------------------------------------------------
    def _add_schedule(self, professional: Professional, payload: ScheduleCreate) -> ProfessionalSchedule:
        overlapping = self.schedules.find_overlapping(
            professional.id, payload.weekday, payload.start_time, payload.end_time
        )
        if overlapping is not None:
            raise ConflictError(
                "A faixa de horario se sobrepoe a outra ja cadastrada "
                f"({overlapping.start_time}-{overlapping.end_time}) em {overlapping.weekday_name}."
            )
        schedule = ProfessionalSchedule(
            professional_id=professional.id,
            weekday=payload.weekday,
            start_time=payload.start_time,
            end_time=payload.end_time,
            slot_duration_minutes=payload.slot_duration_minutes,
            is_active=payload.is_active,
        )
        self.db.add(schedule)
        self.db.flush()
        return schedule

    def add_schedule(
        self, professional_id: int, payload: ScheduleCreate, actor: User
    ) -> ProfessionalSchedule:
        professional = self.get(professional_id)
        self.ensure_can_manage_schedule(actor, professional)
        schedule = self._add_schedule(professional, payload)

        self.audit.record(
            action=AuditAction.SCHEDULE_CREATED,
            actor=actor,
            resource_type="professional_schedule",
            resource_id=schedule.id,
            description=(
                f"Disponibilidade {schedule.weekday_name} "
                f"{schedule.start_time}-{schedule.end_time} cadastrada para "
                f"'{professional.full_name}'."
            ),
        )
        self.db.commit()
        self.db.refresh(schedule)
        return schedule

    def list_schedules(
        self, professional_id: int, *, only_active: bool = False
    ) -> list[ProfessionalSchedule]:
        self.get(professional_id)
        return self.schedules.list_for_professional(professional_id, only_active=only_active)

    def update_schedule(
        self, professional_id: int, schedule_id: int, payload: ScheduleUpdate, actor: User
    ) -> ProfessionalSchedule:
        professional = self.get(professional_id)
        self.ensure_can_manage_schedule(actor, professional)

        schedule = self.schedules.get(schedule_id)
        if schedule is None or schedule.professional_id != professional.id:
            raise NotFoundError(f"Agenda {schedule_id} nao encontrada para este profissional.")

        data = payload.model_dump(exclude_unset=True)
        weekday = data.get("weekday", schedule.weekday)
        start_time = data.get("start_time", schedule.start_time)
        end_time = data.get("end_time", schedule.end_time)
        if end_time <= start_time:
            raise BusinessRuleError("O horario final deve ser posterior ao horario inicial.")

        overlapping = self.schedules.find_overlapping(
            professional.id, weekday, start_time, end_time, exclude_id=schedule.id
        )
        if overlapping is not None:
            raise ConflictError("A faixa de horario se sobrepoe a outra ja cadastrada.")

        for field, value in data.items():
            setattr(schedule, field, value)
        self.db.flush()

        self.audit.record(
            action=AuditAction.SCHEDULE_UPDATED,
            actor=actor,
            resource_type="professional_schedule",
            resource_id=schedule.id,
            description=f"Disponibilidade atualizada para '{professional.full_name}'.",
        )
        self.db.commit()
        self.db.refresh(schedule)
        return schedule

    def delete_schedule(self, professional_id: int, schedule_id: int, actor: User) -> None:
        professional = self.get(professional_id)
        self.ensure_can_manage_schedule(actor, professional)

        schedule = self.schedules.get(schedule_id)
        if schedule is None or schedule.professional_id != professional.id:
            raise NotFoundError(f"Agenda {schedule_id} nao encontrada para este profissional.")

        self.db.delete(schedule)
        self.db.flush()
        self.audit.record(
            action=AuditAction.SCHEDULE_DELETED,
            actor=actor,
            resource_type="professional_schedule",
            resource_id=schedule_id,
            description=f"Disponibilidade removida de '{professional.full_name}'.",
        )
        self.db.commit()

    # ------------------------------------------------------------------
    # Disponibilidade calculada
    # ------------------------------------------------------------------
    def find_schedule_for(
        self, professional_id: int, start: datetime, end: datetime
    ) -> ProfessionalSchedule | None:
        """Faixa ativa que cobre integralmente o intervalo pedido.

        Consultas nao podem atravessar a meia-noite: a agenda e definida por
        dia da semana, entao um intervalo que cruza o dia nunca e valido.
        """
        if start.date() != end.date():
            return None
        schedules = self.schedules.list_for_professional(
            professional_id, weekday=start.weekday(), only_active=True
        )
        for schedule in schedules:
            if schedule.covers(start.time(), end.time()):
                return schedule
        return None

    def build_slots(self, professional_id: int, day: date) -> list[dict]:
        """Grade de horarios do dia, marcando os que ja estao ocupados."""
        professional = self.get(professional_id)
        schedules = self.schedules.list_for_professional(
            professional.id, weekday=day.weekday(), only_active=True
        )
        booked = self.appointments.list_for_day(professional.id, day)
        occupied = [
            (appointment.scheduled_start, appointment.scheduled_end)
            for appointment in booked
            if appointment.occupies_agenda
        ]
        reference = now()

        slots: list[dict] = []
        for schedule in schedules:
            cursor = combine(day, schedule.start_time)
            window_end = combine(day, schedule.end_time)
            step = timedelta(minutes=schedule.slot_duration_minutes)
            while cursor + step <= window_end:
                slot_end = cursor + step
                is_free = cursor >= reference and not any(
                    cursor < busy_end and slot_end > busy_start
                    for busy_start, busy_end in occupied
                )
                slots.append({"start": cursor, "end": slot_end, "available": is_free})
                cursor = slot_end
        slots.sort(key=lambda item: item["start"])
        return slots
