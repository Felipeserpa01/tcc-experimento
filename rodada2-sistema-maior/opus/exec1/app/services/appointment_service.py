"""Regras de agendamento: conflitos, disponibilidade, ciclo de vida e lista de espera."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.datetime_utils import now
from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ScheduleConflictError,
    ValidationFailedError,
)
from app.core.pagination import PaginationParams
from app.models.appointment import Appointment, WaitlistEntry
from app.models.enums import (
    FRONT_DESK_ROLES,
    STAFF_ROLES,
    AppointmentStatus,
    NotificationType,
    UserRole,
    WaitlistStatus,
)
from app.models.patient import Patient
from app.models.professional import Professional
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository, WaitlistRepository
from app.repositories.patient_repository import PatientRepository
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentReschedule,
    AppointmentUpdate,
    WaitlistCreate,
)
from app.services.audit_service import AuditAction, AuditService
from app.services.notification_service import NotificationService
from app.services.professional_service import ProfessionalService

settings = get_settings()

#: Perfis que podem criar/alterar agendamentos de qualquer paciente.
SCHEDULING_ROLES = frozenset({UserRole.ADMIN, UserRole.RECEPTIONIST, UserRole.NURSE})


class AppointmentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = AppointmentRepository(db)
        self.waitlist = WaitlistRepository(db)
        self.patients = PatientRepository(db)
        self.professionals = ProfessionalService(db)
        self.notifications = NotificationService(db)
        self.audit = AuditService(db)

    # ==================================================================
    # Autorizacao
    # ==================================================================
    def _resolve_patient(self, actor: User, patient_id: int | None) -> Patient:
        """Paciente agenda para si; a equipe precisa informar `patient_id`."""
        if actor.role == UserRole.PATIENT:
            own = self.patients.get_by_user_id(actor.id)
            if own is None:
                raise NotFoundError("Nenhum cadastro de paciente vinculado a este usuario.")
            if patient_id is not None and patient_id != own.id:
                raise PermissionDeniedError("Voce so pode agendar consultas para si mesmo.")
            return own

        if patient_id is None:
            raise ValidationFailedError("Informe `patient_id` para agendar a consulta.")
        patient = self.patients.get(patient_id)
        if patient is None:
            raise NotFoundError(f"Paciente {patient_id} nao encontrado.")
        return patient

    def ensure_can_view(self, actor: User, appointment: Appointment) -> None:
        if actor.role in FRONT_DESK_ROLES or actor.role == UserRole.NURSE:
            return
        if actor.role == UserRole.DOCTOR:
            professional = self.professionals.repository.get_by_user_id(actor.id)
            if professional and professional.id == appointment.professional_id:
                return
            raise PermissionDeniedError("Voce so pode acessar as consultas da sua agenda.")
        if actor.role == UserRole.PATIENT:
            patient = self.patients.get_by_user_id(actor.id)
            if patient and patient.id == appointment.patient_id:
                return
        raise PermissionDeniedError("Voce nao tem permissao para acessar esta consulta.")

    def ensure_can_change(self, actor: User, appointment: Appointment) -> None:
        """Confirmar/cancelar/remarcar: equipe, medico responsavel ou o proprio paciente."""
        if actor.role in SCHEDULING_ROLES:
            return
        if actor.role == UserRole.DOCTOR:
            professional = self.professionals.repository.get_by_user_id(actor.id)
            if professional and professional.id == appointment.professional_id:
                return
            raise PermissionDeniedError("Voce so pode alterar consultas da sua agenda.")
        if actor.role == UserRole.PATIENT:
            patient = self.patients.get_by_user_id(actor.id)
            if patient and patient.id == appointment.patient_id:
                return
        raise PermissionDeniedError("Voce nao tem permissao para alterar esta consulta.")

    def ensure_is_responsible_doctor(self, actor: User, appointment: Appointment) -> Professional:
        """Somente o medico responsavel pela consulta pode executar a acao."""
        if actor.role != UserRole.DOCTOR:
            raise PermissionDeniedError("Apenas o medico responsavel pode executar esta acao.")
        professional = self.professionals.repository.get_by_user_id(actor.id)
        if professional is None or professional.id != appointment.professional_id:
            raise PermissionDeniedError(
                "Apenas o medico responsavel por esta consulta pode executar esta acao."
            )
        return professional

    # ==================================================================
    # Validacoes de agendamento
    # ==================================================================
    def _validate_slot(
        self,
        professional: Professional,
        patient: Patient,
        start: datetime,
        duration_minutes: int,
        *,
        exclude_appointment_id: int | None = None,
    ) -> datetime:
        end = start + timedelta(minutes=duration_minutes)
        reference = now()

        # 1. Nunca no passado.
        if start <= reference:
            raise BusinessRuleError(
                "Nao e possivel agendar em data ou horario passado.",
                details={"requested_start": start.isoformat(), "now": reference.isoformat()},
            )

        # 2. Profissional precisa estar ativo e ser medico.
        if not professional.is_active:
            raise BusinessRuleError(f"O profissional '{professional.full_name}' esta inativo.")
        if not patient.is_active:
            raise BusinessRuleError(f"O paciente '{patient.full_name}' esta inativo.")

        # 3. Dentro da agenda de disponibilidade cadastrada.
        schedule = self.professionals.find_schedule_for(professional.id, start, end)
        if schedule is None:
            available = self.professionals.schedules.list_for_professional(
                professional.id, weekday=start.weekday(), only_active=True
            )
            raise BusinessRuleError(
                "Horario fora da agenda de disponibilidade do profissional.",
                details={
                    "weekday": start.weekday(),
                    "requested": f"{start.time()}-{end.time()}",
                    "available_windows": [
                        f"{item.start_time}-{item.end_time}" for item in available
                    ]
                    or "nenhuma faixa cadastrada para este dia da semana",
                },
            )

        # 4. Sem conflito na agenda do profissional.
        conflicts = self.repository.find_conflicts(
            professional.id, start, end, exclude_id=exclude_appointment_id
        )
        if conflicts:
            conflict = conflicts[0]
            raise ScheduleConflictError(
                "O profissional ja possui uma consulta neste horario.",
                details={
                    "conflicting_appointment_id": conflict.id,
                    "conflicting_window": (
                        f"{conflict.scheduled_start.isoformat()} -> "
                        f"{conflict.scheduled_end.isoformat()}"
                    ),
                },
            )

        # 5. Sem conflito na agenda do proprio paciente.
        patient_conflicts = self.repository.find_patient_conflicts(
            patient.id, start, end, exclude_id=exclude_appointment_id
        )
        if patient_conflicts:
            raise ScheduleConflictError(
                "O paciente ja possui outra consulta marcada neste horario.",
                details={"conflicting_appointment_id": patient_conflicts[0].id},
            )

        return end

    # ==================================================================
    # CRUD / ciclo de vida
    # ==================================================================
    def get(self, appointment_id: int, actor: User) -> Appointment:
        appointment = self.repository.get(appointment_id)
        if appointment is None:
            raise NotFoundError(f"Consulta {appointment_id} nao encontrada.")
        self.ensure_can_view(actor, appointment)
        return appointment

    def search(
        self,
        pagination: PaginationParams,
        actor: User,
        *,
        patient_id: int | None = None,
        professional_id: int | None = None,
        status: AppointmentStatus | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[list[Appointment], int]:
        # Escopo obrigatorio por perfil.
        if actor.role == UserRole.PATIENT:
            own = self.patients.get_by_user_id(actor.id)
            if own is None:
                return [], 0
            if patient_id is not None and patient_id != own.id:
                raise PermissionDeniedError("Voce so pode consultar os proprios agendamentos.")
            patient_id = own.id
        elif actor.role == UserRole.DOCTOR:
            professional = self.professionals.repository.get_by_user_id(actor.id)
            if professional is None:
                return [], 0
            if professional_id is not None and professional_id != professional.id:
                raise PermissionDeniedError("Voce so pode consultar a sua propria agenda.")
            professional_id = professional.id

        return self.repository.search(
            pagination,
            patient_id=patient_id,
            professional_id=professional_id,
            status=status,
            start_date=start_date,
            end_date=end_date,
        )

    def create(self, payload: AppointmentCreate, actor: User) -> Appointment:
        if actor.role not in SCHEDULING_ROLES and actor.role != UserRole.PATIENT:
            raise PermissionDeniedError("Seu perfil nao pode criar agendamentos.")

        patient = self._resolve_patient(actor, payload.patient_id)
        professional = self.professionals.get_doctor(payload.professional_id)

        duration = (
            payload.duration_minutes
            or professional.appointment_duration_minutes
            or settings.default_appointment_duration_minutes
        )
        end = self._validate_slot(professional, patient, payload.scheduled_start, duration)

        appointment = Appointment(
            patient_id=patient.id,
            professional_id=professional.id,
            scheduled_start=payload.scheduled_start,
            scheduled_end=end,
            duration_minutes=duration,
            status=AppointmentStatus.SCHEDULED,
            reason=payload.reason,
            notes=payload.notes,
            created_by_id=actor.id,
        )
        self.db.add(appointment)
        self.db.flush()

        self._close_matching_waitlist(appointment)

        self.audit.record(
            action=AuditAction.APPOINTMENT_CREATED,
            actor=actor,
            resource_type="appointment",
            resource_id=appointment.id,
            description=(
                f"Consulta agendada para '{patient.full_name}' com "
                f"'{professional.full_name}' em {appointment.scheduled_start:%d/%m/%Y %H:%M}."
            ),
        )
        self.db.commit()
        self.db.refresh(appointment)
        return appointment

    def update_details(
        self, appointment_id: int, payload: AppointmentUpdate, actor: User
    ) -> Appointment:
        appointment = self.repository.get(appointment_id)
        if appointment is None:
            raise NotFoundError(f"Consulta {appointment_id} nao encontrada.")
        self.ensure_can_change(actor, appointment)
        if appointment.is_final:
            raise BusinessRuleError(
                f"Consulta com status '{appointment.status.value}' nao pode mais ser editada."
            )

        data = payload.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(appointment, field, value)
        self.db.flush()

        self.audit.record(
            action=AuditAction.APPOINTMENT_UPDATED,
            actor=actor,
            resource_type="appointment",
            resource_id=appointment.id,
            description="Dados da consulta atualizados.",
            extra={"fields": sorted(data.keys())},
        )
        self.db.commit()
        self.db.refresh(appointment)
        return appointment

    # ------------------------------------------------------------------
    def _transition(
        self, appointment: Appointment, target: AppointmentStatus
    ) -> None:
        if appointment.status == target:
            raise ConflictError(f"A consulta ja esta com status '{target.value}'.")
        if not appointment.can_transition_to(target):
            raise BusinessRuleError(
                f"Transicao invalida: '{appointment.status.value}' -> '{target.value}'."
            )
        appointment.status = target

    def confirm(self, appointment_id: int, actor: User) -> Appointment:
        appointment = self.repository.get(appointment_id)
        if appointment is None:
            raise NotFoundError(f"Consulta {appointment_id} nao encontrada.")
        self.ensure_can_change(actor, appointment)

        self._transition(appointment, AppointmentStatus.CONFIRMED)
        appointment.confirmed_at = now()
        self.db.flush()

        self.notifications.notify(
            user_id=appointment.patient.user_id,
            notification_type=NotificationType.APPOINTMENT_CONFIRMED,
            title="Consulta confirmada",
            message=(
                f"Sua consulta de {appointment.scheduled_start:%d/%m/%Y as %H:%M} "
                f"com {appointment.professional.full_name} foi confirmada."
            ),
            resource_type="appointment",
            resource_id=appointment.id,
        )
        self.audit.record(
            action=AuditAction.APPOINTMENT_CONFIRMED,
            actor=actor,
            resource_type="appointment",
            resource_id=appointment.id,
            description="Consulta confirmada.",
        )
        self.db.commit()
        self.db.refresh(appointment)
        return appointment

    def cancel(self, appointment_id: int, reason: str, actor: User) -> Appointment:
        appointment = self.repository.get(appointment_id)
        if appointment is None:
            raise NotFoundError(f"Consulta {appointment_id} nao encontrada.")
        self.ensure_can_change(actor, appointment)

        self._transition(appointment, AppointmentStatus.CANCELLED)
        appointment.cancelled_at = now()
        appointment.cancellation_reason = reason
        appointment.cancelled_by_id = actor.id
        self.db.flush()

        self.notifications.notify(
            user_id=appointment.patient.user_id,
            notification_type=NotificationType.APPOINTMENT_CANCELLED,
            title="Consulta cancelada",
            message=(
                f"Sua consulta de {appointment.scheduled_start:%d/%m/%Y as %H:%M} "
                f"foi cancelada. Motivo: {reason}"
            ),
            resource_type="appointment",
            resource_id=appointment.id,
        )
        notified = self._notify_waitlist(appointment)

        self.audit.record(
            action=AuditAction.APPOINTMENT_CANCELLED,
            actor=actor,
            resource_type="appointment",
            resource_id=appointment.id,
            description=f"Consulta cancelada. Motivo: {reason}",
            extra={"waitlist_notified": notified},
        )
        self.db.commit()
        self.db.refresh(appointment)
        return appointment

    def reschedule(
        self, appointment_id: int, payload: AppointmentReschedule, actor: User
    ) -> Appointment:
        original = self.repository.get(appointment_id)
        if original is None:
            raise NotFoundError(f"Consulta {appointment_id} nao encontrada.")
        self.ensure_can_change(actor, original)

        if original.is_final:
            raise BusinessRuleError(
                f"Consulta com status '{original.status.value}' nao pode ser remarcada."
            )
        if original.status == AppointmentStatus.IN_PROGRESS:
            raise BusinessRuleError("Consulta em andamento nao pode ser remarcada.")

        professional = self.professionals.get_doctor(original.professional_id)
        patient = self.patients.get(original.patient_id)
        duration = payload.duration_minutes or original.duration_minutes
        previous_start = original.scheduled_start

        end = self._validate_slot(
            professional,
            patient,
            payload.scheduled_start,
            duration,
            exclude_appointment_id=original.id,
        )

        original.scheduled_start = payload.scheduled_start
        original.scheduled_end = end
        original.duration_minutes = duration
        original.status = AppointmentStatus.SCHEDULED
        original.confirmed_at = None
        if payload.reason:
            original.notes = (
                f"{original.notes}\n" if original.notes else ""
            ) + f"Remarcada: {payload.reason}"
        self.db.flush()

        self.notifications.notify(
            user_id=patient.user_id,
            notification_type=NotificationType.APPOINTMENT_RESCHEDULED,
            title="Consulta remarcada",
            message=(
                f"Sua consulta foi remarcada de {previous_start:%d/%m/%Y as %H:%M} "
                f"para {original.scheduled_start:%d/%m/%Y as %H:%M}."
            ),
            resource_type="appointment",
            resource_id=original.id,
        )
        # O horario antigo ficou livre: avisa quem estava na lista de espera.
        notified = self._notify_waitlist_for_slot(
            original.professional_id, previous_start, exclude_patient_id=patient.id
        )

        self.audit.record(
            action=AuditAction.APPOINTMENT_RESCHEDULED,
            actor=actor,
            resource_type="appointment",
            resource_id=original.id,
            description=(
                f"Consulta remarcada de {previous_start:%d/%m/%Y %H:%M} "
                f"para {original.scheduled_start:%d/%m/%Y %H:%M}."
            ),
            extra={"waitlist_notified": notified},
        )
        self.db.commit()
        self.db.refresh(original)
        return original

    def start(self, appointment_id: int, actor: User) -> Appointment:
        appointment = self.repository.get(appointment_id)
        if appointment is None:
            raise NotFoundError(f"Consulta {appointment_id} nao encontrada.")
        self.ensure_is_responsible_doctor(actor, appointment)

        self._transition(appointment, AppointmentStatus.IN_PROGRESS)
        appointment.started_at = now()
        self.db.flush()

        self.audit.record(
            action=AuditAction.APPOINTMENT_STARTED,
            actor=actor,
            resource_type="appointment",
            resource_id=appointment.id,
            description="Atendimento iniciado.",
        )
        self.db.commit()
        self.db.refresh(appointment)
        return appointment

    def complete(self, appointment_id: int, actor: User) -> Appointment:
        appointment = self.repository.get(appointment_id)
        if appointment is None:
            raise NotFoundError(f"Consulta {appointment_id} nao encontrada.")
        self.ensure_is_responsible_doctor(actor, appointment)

        self._transition(appointment, AppointmentStatus.COMPLETED)
        appointment.completed_at = now()
        self.db.flush()

        self.audit.record(
            action=AuditAction.APPOINTMENT_COMPLETED,
            actor=actor,
            resource_type="appointment",
            resource_id=appointment.id,
            description="Atendimento concluido.",
        )
        self.db.commit()
        self.db.refresh(appointment)
        return appointment

    def mark_no_show(self, appointment_id: int, actor: User) -> Appointment:
        appointment = self.repository.get(appointment_id)
        if appointment is None:
            raise NotFoundError(f"Consulta {appointment_id} nao encontrada.")
        if actor.role not in STAFF_ROLES:
            raise PermissionDeniedError("Apenas a equipe da clinica registra faltas.")
        if actor.role == UserRole.DOCTOR:
            own = self.professionals.repository.get_by_user_id(actor.id)
            if own is None or own.id != appointment.professional_id:
                raise PermissionDeniedError(
                    "Voce so pode registrar faltas nas consultas da sua agenda."
                )

        if appointment.scheduled_start > now():
            raise BusinessRuleError(
                "Nao e possivel registrar falta antes do horario da consulta."
            )
        self._transition(appointment, AppointmentStatus.NO_SHOW)
        self.db.flush()

        self.audit.record(
            action=AuditAction.APPOINTMENT_NO_SHOW,
            actor=actor,
            resource_type="appointment",
            resource_id=appointment.id,
            description="Falta do paciente registrada.",
        )
        self.db.commit()
        self.db.refresh(appointment)
        return appointment

    # ------------------------------------------------------------------
    # Agenda do dia
    # ------------------------------------------------------------------
    def daily_agenda(self, professional_id: int, day: date, actor: User) -> dict:
        professional = self.professionals.get(professional_id)
        if actor.role == UserRole.PATIENT:
            raise PermissionDeniedError("Pacientes nao acessam a agenda completa do profissional.")
        if actor.role == UserRole.DOCTOR:
            own = self.professionals.repository.get_by_user_id(actor.id)
            if own is None or own.id != professional.id:
                raise PermissionDeniedError("Voce so pode visualizar a sua propria agenda.")

        appointments = self.repository.list_for_day(professional.id, day)
        items = [
            {
                "id": appointment.id,
                "scheduled_start": appointment.scheduled_start,
                "scheduled_end": appointment.scheduled_end,
                "status": appointment.status,
                "patient_id": appointment.patient_id,
                "patient_name": appointment.patient.full_name,
                "reason": appointment.reason,
            }
            for appointment in appointments
        ]
        return {
            "professional_id": professional.id,
            "professional_name": professional.full_name,
            "date": day,
            "total": len(items),
            "appointments": items,
        }

    # ==================================================================
    # Lista de espera
    # ==================================================================
    def add_to_waitlist(self, payload: WaitlistCreate, actor: User) -> WaitlistEntry:
        patient = self._resolve_patient(actor, payload.patient_id)
        professional = self.professionals.get_doctor(payload.professional_id)

        if payload.desired_date < now().date():
            raise BusinessRuleError("A data desejada nao pode estar no passado.")

        duplicated = self.waitlist.find_duplicate(patient.id, professional.id, payload.desired_date)
        if duplicated is not None:
            raise ConflictError(
                "O paciente ja esta na lista de espera deste profissional para esta data.",
                details={"waitlist_entry_id": duplicated.id},
            )

        entry = WaitlistEntry(
            patient_id=patient.id,
            professional_id=professional.id,
            desired_date=payload.desired_date,
            preferred_start_time=payload.preferred_start_time,
            preferred_end_time=payload.preferred_end_time,
            notes=payload.notes,
            status=WaitlistStatus.WAITING,
            created_by_id=actor.id,
        )
        self.db.add(entry)
        self.db.flush()

        self.audit.record(
            action=AuditAction.WAITLIST_CREATED,
            actor=actor,
            resource_type="waitlist_entry",
            resource_id=entry.id,
            description=(
                f"'{patient.full_name}' entrou na lista de espera de "
                f"'{professional.full_name}' para {payload.desired_date:%d/%m/%Y}."
            ),
        )
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def search_waitlist(
        self,
        pagination: PaginationParams,
        actor: User,
        *,
        patient_id: int | None = None,
        professional_id: int | None = None,
        status: WaitlistStatus | None = None,
        desired_date: date | None = None,
    ) -> tuple[list[WaitlistEntry], int]:
        if actor.role == UserRole.PATIENT:
            own = self.patients.get_by_user_id(actor.id)
            if own is None:
                return [], 0
            patient_id = own.id
        elif actor.role == UserRole.DOCTOR:
            professional = self.professionals.repository.get_by_user_id(actor.id)
            if professional is None:
                return [], 0
            professional_id = professional.id

        return self.waitlist.search(
            pagination,
            patient_id=patient_id,
            professional_id=professional_id,
            status=status,
            desired_date=desired_date,
        )

    def cancel_waitlist_entry(self, entry_id: int, actor: User) -> WaitlistEntry:
        entry = self.waitlist.get(entry_id)
        if entry is None:
            raise NotFoundError(f"Entrada {entry_id} da lista de espera nao encontrada.")

        if actor.role == UserRole.PATIENT:
            own = self.patients.get_by_user_id(actor.id)
            if own is None or own.id != entry.patient_id:
                raise PermissionDeniedError("Voce so pode sair da propria lista de espera.")
        elif actor.role not in SCHEDULING_ROLES and actor.role != UserRole.DOCTOR:
            raise PermissionDeniedError("Perfil sem permissao para alterar a lista de espera.")

        if not entry.is_open:
            raise ConflictError(f"Entrada ja esta com status '{entry.status.value}'.")

        entry.status = WaitlistStatus.CANCELLED
        self.db.flush()

        self.audit.record(
            action=AuditAction.WAITLIST_CANCELLED,
            actor=actor,
            resource_type="waitlist_entry",
            resource_id=entry.id,
            description="Entrada removida da lista de espera.",
        )
        self.db.commit()
        self.db.refresh(entry)
        return entry

    # ------------------------------------------------------------------
    def _notify_waitlist(self, appointment: Appointment) -> int:
        return self._notify_waitlist_for_slot(
            appointment.professional_id,
            appointment.scheduled_start,
            exclude_patient_id=appointment.patient_id,
        )

    def _notify_waitlist_for_slot(
        self, professional_id: int, slot_start: datetime, *, exclude_patient_id: int | None = None
    ) -> int:
        """Avisa os pacientes da lista de espera que o horario vagou."""
        if slot_start <= now():
            return 0

        matches = self.waitlist.find_open_matches(professional_id, slot_start)
        notified = 0
        for entry in matches:
            if exclude_patient_id and entry.patient_id == exclude_patient_id:
                continue
            entry.status = WaitlistStatus.NOTIFIED
            entry.notified_at = now()
            entry.notified_slot_start = slot_start
            self.notifications.notify(
                user_id=entry.patient.user_id,
                notification_type=NotificationType.WAITLIST_SLOT_AVAILABLE,
                title="Horario disponivel",
                message=(
                    f"Abriu um horario com {entry.professional.full_name} em "
                    f"{slot_start:%d/%m/%Y as %H:%M}. Entre em contato para confirmar."
                ),
                resource_type="waitlist_entry",
                resource_id=entry.id,
            )
            notified += 1

        if notified:
            self.audit.record(
                action=AuditAction.WAITLIST_NOTIFIED,
                resource_type="professional",
                resource_id=professional_id,
                description=(
                    f"{notified} paciente(s) da lista de espera notificado(s) sobre o "
                    f"horario de {slot_start:%d/%m/%Y %H:%M}."
                ),
            )
        self.db.flush()
        return notified

    def _close_matching_waitlist(self, appointment: Appointment) -> None:
        """Quando o paciente consegue agendar, sua espera e encerrada."""
        entry = self.waitlist.find_duplicate(
            appointment.patient_id,
            appointment.professional_id,
            appointment.scheduled_start.date(),
        )
        if entry is not None:
            entry.status = WaitlistStatus.FULFILLED
            entry.fulfilled_appointment_id = appointment.id
            self.db.flush()
