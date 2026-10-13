"""Agendamento de consultas e ciclo de vida do atendimento."""

from datetime import date, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import clock
from app.core.config import get_settings
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.pagination import PageParams, PageResult, SortParams
from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus, Role
from app.models.patient import Patient
from app.models.professional import Professional
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.patient_repository import PatientRepository
from app.schemas.appointment import AppointmentCreate
from app.services import access, scheduling
from app.services.audit_service import AuditAction, AuditService
from app.services.notification_service import NotificationService
from app.services.professional_service import ProfessionalService
from app.services.waitlist_service import WaitlistService

SLOT_TAKEN_MESSAGE = "O médico já possui uma consulta neste horário. Você pode entrar na lista de espera."


class AppointmentService:
    def __init__(self, db: Session, notifications: NotificationService) -> None:
        self.db = db
        self.settings = get_settings()
        self.appointments = AppointmentRepository(db)
        self.patients = PatientRepository(db)
        self.professionals = ProfessionalService(db)
        self.waitlist = WaitlistService(db, notifications)
        self.notifications = notifications
        self.audit = AuditService(db)

    # ------------------------------------------------------------------ consulta
    def get(self, actor: User, appointment_id: int) -> Appointment:
        appointment = self.appointments.get(appointment_id)
        if appointment is None:
            raise NotFoundError("Consulta não encontrada.")
        access.ensure_appointment_scope(actor, appointment)
        return appointment

    def search(
        self,
        actor: User,
        page: PageParams,
        sort: SortParams,
        *,
        patient_id: int | None = None,
        professional_id: int | None = None,
        status: AppointmentStatus | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> PageResult[Appointment]:
        if date_from and date_to and date_from > date_to:
            raise BusinessRuleError("'date_from' deve ser anterior ou igual a 'date_to'.")
        if access.is_patient(actor):
            patient_id = access.own_patient_id(actor)
        return self.appointments.search(
            page,
            sort,
            patient_id=patient_id,
            professional_id=professional_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
        )

    def daily_agenda(
        self, professional_id: int, day: date, include_cancelled: bool
    ) -> tuple[Professional, list[Appointment]]:
        professional = self.professionals.get(professional_id)
        if not professional.is_doctor:
            raise BusinessRuleError("Agenda de consultas disponível apenas para médicos.")
        statuses = None if include_cancelled else [s for s in AppointmentStatus if s != AppointmentStatus.CANCELLED]
        return professional, self.appointments.list_for_professional_on(professional.id, day, statuses=statuses)

    # ------------------------------------------------------------------ validações de horário
    def _validate_new_slot(
        self,
        professional: Professional,
        patient_id: int,
        start_at: datetime,
        exclude_id: int | None = None,
    ) -> scheduling.Slot:
        now = clock.now()
        if start_at <= now:
            raise BusinessRuleError(
                "Não é possível agendar consultas em data ou horário passado.", code="horario_passado"
            )
        max_days = self.settings.max_booking_days_ahead
        if start_at.date() > now.date() + timedelta(days=max_days):
            raise BusinessRuleError(f"Agendamentos podem ser feitos com no máximo {max_days} dias de antecedência.")
        slot = scheduling.resolve_slot(professional.availabilities, start_at)

        if self.appointments.find_overlapping(
            slot.start_at, slot.end_at, professional_id=professional.id, exclude_id=exclude_id
        ):
            raise ConflictError(
                SLOT_TAKEN_MESSAGE, code="horario_ocupado", details={"lista_de_espera_disponivel": True}
            )
        if self.appointments.find_overlapping(slot.start_at, slot.end_at, patient_id=patient_id, exclude_id=exclude_id):
            raise ConflictError("O paciente já possui outra consulta neste horário.", code="conflito_paciente")
        return slot

    def _resolve_patient(self, actor: User, requested_patient_id: int | None) -> Patient:
        if access.is_patient(actor):
            if requested_patient_id is not None:
                access.ensure_patient_scope(actor, requested_patient_id)
            requested_patient_id = access.own_patient_id(actor)
        if requested_patient_id is None:
            raise BusinessRuleError("Informe o paciente ('patient_id').")
        patient = self.patients.get(requested_patient_id)
        if patient is None:
            raise NotFoundError("Paciente não encontrado.")
        if not patient.is_active:
            raise BusinessRuleError("Não é possível agendar para um paciente inativo.")
        return patient

    def _flush_guarding_slot(self) -> None:
        """Converte a violação do índice único (corrida entre requisições) em conflito de horário."""
        try:
            self.db.flush()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError(SLOT_TAKEN_MESSAGE, code="horario_ocupado") from exc

    # ------------------------------------------------------------------ agendamento
    def schedule(self, actor: User, data: AppointmentCreate) -> Appointment:
        patient = self._resolve_patient(actor, data.patient_id)
        professional = self.professionals.get_active_doctor(data.professional_id)
        slot = self._validate_new_slot(professional, patient.id, data.start_at)

        appointment = Appointment(
            patient_id=patient.id,
            professional_id=professional.id,
            start_at=slot.start_at,
            end_at=slot.end_at,
            status=AppointmentStatus.SCHEDULED,
            reason=data.reason,
            created_by_id=actor.id,
            reschedule_count=0,
        )
        self.db.add(appointment)
        self._flush_guarding_slot()
        self.waitlist.mark_booked(patient.id, professional.id, slot.start_at, slot.end_at)
        self.notifications.notify_patient(
            patient,
            "Consulta agendada",
            f"Sua consulta com {professional.full_name} foi agendada para "
            f"{slot.start_at.strftime('%d/%m/%Y às %H:%M')}.",
        )
        self.audit.log(
            AuditAction.APPOINTMENT_CREATED,
            actor=actor,
            entity_type="consulta",
            entity_id=appointment.id,
            details={"inicio": slot.start_at.isoformat(), "profissional_id": professional.id},
        )
        self.db.commit()
        self.db.refresh(appointment)
        return appointment

    def confirm(self, actor: User, appointment_id: int) -> Appointment:
        appointment = self.get(actor, appointment_id)
        access.ensure_can_manage_appointment(actor, appointment)
        scheduling.ensure_transition(appointment.status, AppointmentStatus.CONFIRMED)
        if appointment.start_at <= clock.now():
            raise BusinessRuleError("Não é possível confirmar uma consulta cujo horário já passou.")
        appointment.status = AppointmentStatus.CONFIRMED
        appointment.confirmed_at = clock.now()
        self.audit.log(AuditAction.APPOINTMENT_CONFIRMED, actor=actor, entity_type="consulta", entity_id=appointment.id)
        self.db.commit()
        return appointment

    def cancel(self, actor: User, appointment_id: int, reason: str) -> Appointment:
        appointment = self.get(actor, appointment_id)
        access.ensure_can_manage_appointment(actor, appointment)
        scheduling.ensure_transition(appointment.status, AppointmentStatus.CANCELLED)
        now = clock.now()
        if appointment.start_at <= now:
            raise BusinessRuleError(
                "Não é possível cancelar uma consulta cujo horário já passou. Registre a falta, se for o caso."
            )
        appointment.status = AppointmentStatus.CANCELLED
        appointment.cancellation_reason = reason
        appointment.cancelled_at = now
        appointment.cancelled_by_id = actor.id
        self.db.flush()
        notified = self.waitlist.notify_slot_released(
            appointment.professional, appointment.start_at, appointment.end_at
        )
        self.audit.log(
            AuditAction.APPOINTMENT_CANCELLED,
            actor=actor,
            entity_type="consulta",
            entity_id=appointment.id,
            details={"motivo": reason, "lista_de_espera_notificados": notified},
        )
        self.db.commit()
        return appointment

    def reschedule(self, actor: User, appointment_id: int, new_start: datetime) -> Appointment:
        appointment = self.get(actor, appointment_id)
        access.ensure_can_manage_appointment(actor, appointment)
        if appointment.status not in (AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED):
            raise BusinessRuleError("Somente consultas agendadas ou confirmadas podem ser remarcadas.")
        if appointment.start_at <= clock.now():
            raise BusinessRuleError("Não é possível remarcar uma consulta cujo horário já passou.")
        if new_start == appointment.start_at:
            raise BusinessRuleError("O novo horário deve ser diferente do atual.")

        professional = self.professionals.get_active_doctor(appointment.professional_id)
        slot = self._validate_new_slot(professional, appointment.patient_id, new_start, exclude_id=appointment.id)
        old_start, old_end = appointment.start_at, appointment.end_at

        appointment.start_at = slot.start_at
        appointment.end_at = slot.end_at
        appointment.status = AppointmentStatus.SCHEDULED  # novo horário precisa de nova confirmação
        appointment.confirmed_at = None
        appointment.reschedule_count += 1
        self._flush_guarding_slot()

        self.waitlist.mark_booked(appointment.patient_id, professional.id, slot.start_at, slot.end_at)
        notified = self.waitlist.notify_slot_released(professional, old_start, old_end)
        self.notifications.notify_patient(
            appointment.patient,
            "Consulta remarcada",
            f"Sua consulta com {professional.full_name} foi remarcada para "
            f"{slot.start_at.strftime('%d/%m/%Y às %H:%M')}.",
        )
        self.audit.log(
            AuditAction.APPOINTMENT_RESCHEDULED,
            actor=actor,
            entity_type="consulta",
            entity_id=appointment.id,
            details={
                "de": old_start.isoformat(),
                "para": slot.start_at.isoformat(),
                "lista_de_espera_notificados": notified,
            },
        )
        self.db.commit()
        return appointment

    # ------------------------------------------------------------------ atendimento
    def start(self, actor: User, appointment_id: int) -> Appointment:
        appointment = self.get(actor, appointment_id)
        access.ensure_responsible_doctor(actor, appointment)
        scheduling.ensure_transition(appointment.status, AppointmentStatus.IN_PROGRESS)
        now = clock.now()
        if appointment.start_at.date() != now.date():
            raise BusinessRuleError("A consulta só pode ser iniciada no dia agendado.")
        appointment.status = AppointmentStatus.IN_PROGRESS
        appointment.started_at = now
        self.audit.log(AuditAction.APPOINTMENT_STARTED, actor=actor, entity_type="consulta", entity_id=appointment.id)
        self.db.commit()
        return appointment

    def complete(self, actor: User, appointment_id: int) -> Appointment:
        appointment = self.get(actor, appointment_id)
        access.ensure_responsible_doctor(actor, appointment)
        scheduling.ensure_transition(appointment.status, AppointmentStatus.COMPLETED)
        appointment.status = AppointmentStatus.COMPLETED
        appointment.completed_at = clock.now()
        self.audit.log(AuditAction.APPOINTMENT_COMPLETED, actor=actor, entity_type="consulta", entity_id=appointment.id)
        self.db.commit()
        return appointment

    def mark_no_show(self, actor: User, appointment_id: int) -> Appointment:
        appointment = self.get(actor, appointment_id)
        if actor.role == Role.DOCTOR:
            access.ensure_responsible_doctor(actor, appointment)
        scheduling.ensure_transition(appointment.status, AppointmentStatus.NO_SHOW)
        now = clock.now()
        if appointment.start_at > now:
            raise BusinessRuleError("A falta só pode ser registrada após o horário marcado da consulta.")
        appointment.status = AppointmentStatus.NO_SHOW
        appointment.no_show_at = now
        self.audit.log(AuditAction.APPOINTMENT_NO_SHOW, actor=actor, entity_type="consulta", entity_id=appointment.id)
        self.db.commit()
        return appointment
