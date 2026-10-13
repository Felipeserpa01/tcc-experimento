"""Appointment scheduling business logic: conflicts, availability, waitlist, status transitions."""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.enums import (
    AppointmentStatus,
    TERMINAL_APPOINTMENT_STATUSES,
    UserRole,
    WaitlistStatus,
)
from app.core.exceptions import BusinessRuleError, ForbiddenError, NotFoundError
from app.models.appointment import Appointment, WaitlistEntry
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.professional_repository import ProfessionalRepository
from app.schemas.appointment import AppointmentCreate, WaitlistCreate
from app.services.audit_service import AuditService

# Valid forward transitions for appointment status.
ALLOWED_TRANSITIONS: dict[AppointmentStatus, set[AppointmentStatus]] = {
    AppointmentStatus.AGENDADA: {
        AppointmentStatus.CONFIRMADA,
        AppointmentStatus.CANCELADA,
        AppointmentStatus.EM_ANDAMENTO,
        AppointmentStatus.FALTOU,
    },
    AppointmentStatus.CONFIRMADA: {
        AppointmentStatus.EM_ANDAMENTO,
        AppointmentStatus.CANCELADA,
        AppointmentStatus.FALTOU,
    },
    AppointmentStatus.EM_ANDAMENTO: {AppointmentStatus.REALIZADA, AppointmentStatus.CANCELADA},
    AppointmentStatus.REALIZADA: set(),
    AppointmentStatus.CANCELADA: set(),
    AppointmentStatus.FALTOU: set(),
}


class AppointmentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AppointmentRepository(db)
        self.patient_repo = PatientRepository(db)
        self.professional_repo = ProfessionalRepository(db)
        self.audit = AuditService(db)

    def _validate_within_availability(self, professional_id: int, start: datetime, end: datetime) -> None:
        professional = self.professional_repo.get_by_id(professional_id)
        if not professional:
            raise NotFoundError("Profissional não encontrado.")

        weekday = start.weekday()
        matching_slots = [s for s in professional.availability_slots if s.dia_semana == weekday]
        if not matching_slots:
            raise BusinessRuleError("Profissional não possui agenda de disponibilidade para este dia.")

        start_time = start.time()
        end_time = end.time()
        for slot in matching_slots:
            if start_time >= slot.hora_inicio and end_time <= slot.hora_fim:
                return
        raise BusinessRuleError(
            "Horário solicitado está fora da agenda de disponibilidade do profissional."
        )

    def schedule(self, data: AppointmentCreate, actor: User, ip_address: str | None = None) -> Appointment:
        patient = self.patient_repo.get_by_id(data.patient_id)
        if not patient:
            raise NotFoundError("Paciente não encontrado.")

        if actor.role == UserRole.PACIENTE and patient.user_id != actor.id:
            raise ForbiddenError("Você só pode agendar consultas para você mesmo.")

        professional = self.professional_repo.get_by_id(data.professional_id)
        if not professional:
            raise NotFoundError("Profissional não encontrado.")

        start = data.data_hora
        end = start + timedelta(minutes=data.duracao_minutos)

        self._validate_within_availability(data.professional_id, start, end)

        conflict = self.repo.find_conflict(data.professional_id, start, end)
        if conflict:
            raise BusinessRuleError(
                "O profissional já possui uma consulta agendada neste horário."
            )

        appointment = Appointment(
            patient_id=data.patient_id,
            professional_id=data.professional_id,
            data_hora=start,
            duracao_minutos=data.duracao_minutos,
            status=AppointmentStatus.AGENDADA,
            created_by=actor.id,
        )
        self.repo.create(appointment)
        self.db.commit()
        self.audit.log(actor.id, "APPOINTMENT_CREATE", "Appointment", appointment.id, ip_address=ip_address)
        self.db.commit()
        return appointment

    def get(self, appointment_id: int, actor: User) -> Appointment:
        appointment = self.repo.get_by_id(appointment_id)
        if not appointment:
            raise NotFoundError("Consulta não encontrada.")
        self._ensure_can_view(appointment, actor)
        return appointment

    def _ensure_can_view(self, appointment: Appointment, actor: User) -> None:
        if actor.role == UserRole.PACIENTE and appointment.patient.user_id != actor.id:
            raise ForbiddenError("Você só pode acessar as suas próprias consultas.")

    def _transition(self, appointment: Appointment, new_status: AppointmentStatus) -> None:
        allowed = ALLOWED_TRANSITIONS.get(appointment.status, set())
        if new_status not in allowed:
            raise BusinessRuleError(
                f"Não é possível alterar o status de '{appointment.status.value}' para '{new_status.value}'."
            )

    def confirm(self, appointment_id: int, actor: User, ip_address: str | None = None) -> Appointment:
        appointment = self.repo.get_by_id(appointment_id)
        if not appointment:
            raise NotFoundError("Consulta não encontrada.")
        if actor.role == UserRole.PACIENTE and appointment.patient.user_id != actor.id:
            raise ForbiddenError("Você só pode confirmar as suas próprias consultas.")
        self._transition(appointment, AppointmentStatus.CONFIRMADA)
        appointment.status = AppointmentStatus.CONFIRMADA
        self.repo.update(appointment)
        self.db.commit()
        self.audit.log(actor.id, "APPOINTMENT_CONFIRM", "Appointment", appointment.id, ip_address=ip_address)
        self.db.commit()
        return appointment

    def update_status(
        self, appointment_id: int, new_status: AppointmentStatus, actor: User, ip_address: str | None = None
    ) -> Appointment:
        appointment = self.repo.get_by_id(appointment_id)
        if not appointment:
            raise NotFoundError("Consulta não encontrada.")
        self._transition(appointment, new_status)
        appointment.status = new_status
        self.repo.update(appointment)
        self.db.commit()
        self.audit.log(
            actor.id, f"APPOINTMENT_STATUS_{new_status.value.upper()}", "Appointment", appointment.id,
            ip_address=ip_address,
        )
        self.db.commit()
        return appointment

    def cancel(
        self, appointment_id: int, motivo: str, actor: User, ip_address: str | None = None
    ) -> Appointment:
        appointment = self.repo.get_by_id(appointment_id)
        if not appointment:
            raise NotFoundError("Consulta não encontrada.")

        if actor.role == UserRole.PACIENTE and appointment.patient.user_id != actor.id:
            raise ForbiddenError("Você só pode cancelar as suas próprias consultas.")

        if appointment.status in TERMINAL_APPOINTMENT_STATUSES:
            raise BusinessRuleError("Esta consulta já está em um status final e não pode ser cancelada.")

        appointment.status = AppointmentStatus.CANCELADA
        appointment.motivo_cancelamento = motivo
        self.repo.update(appointment)
        self.db.commit()
        self.audit.log(actor.id, "APPOINTMENT_CANCEL", "Appointment", appointment.id, ip_address=ip_address)
        self.db.commit()

        self._notify_waitlist(appointment.professional_id, appointment.data_hora.date())
        return appointment

    def reschedule(
        self, appointment_id: int, new_datetime: datetime, actor: User, ip_address: str | None = None
    ) -> Appointment:
        appointment = self.repo.get_by_id(appointment_id)
        if not appointment:
            raise NotFoundError("Consulta não encontrada.")

        if actor.role == UserRole.PACIENTE and appointment.patient.user_id != actor.id:
            raise ForbiddenError("Você só pode remarcar as suas próprias consultas.")

        if appointment.status in TERMINAL_APPOINTMENT_STATUSES:
            raise BusinessRuleError("Esta consulta já está em um status final e não pode ser remarcada.")

        end = new_datetime + timedelta(minutes=appointment.duracao_minutos)
        self._validate_within_availability(appointment.professional_id, new_datetime, end)

        conflict = self.repo.find_conflict(
            appointment.professional_id, new_datetime, end, exclude_appointment_id=appointment.id
        )
        if conflict:
            raise BusinessRuleError("O profissional já possui uma consulta agendada neste horário.")

        old_date = appointment.data_hora.date()
        appointment.data_hora = new_datetime
        appointment.status = AppointmentStatus.AGENDADA
        self.repo.update(appointment)
        self.db.commit()
        self.audit.log(actor.id, "APPOINTMENT_RESCHEDULE", "Appointment", appointment.id, ip_address=ip_address)
        self.db.commit()

        self._notify_waitlist(appointment.professional_id, old_date)
        return appointment

    def search(
        self,
        actor: User,
        patient_id: int | None,
        professional_id: int | None,
        status: AppointmentStatus | None,
        date_from: date | None,
        date_to: date | None,
        page: int,
        page_size: int,
        sort_by: str | None,
        sort_order: str,
    ) -> tuple[list[Appointment], int]:
        if actor.role == UserRole.PACIENTE:
            own_patient = self.patient_repo.get_by_user_id(actor.id)
            if not own_patient:
                raise NotFoundError("Cadastro de paciente não encontrado para este usuário.")
            patient_id = own_patient.id

        return self.repo.search(
            patient_id, professional_id, status, date_from, date_to, page, page_size, sort_by, sort_order
        )

    def get_daily_agenda(self, professional_id: int, day: date) -> list[Appointment]:
        professional = self.professional_repo.get_by_id(professional_id)
        if not professional:
            raise NotFoundError("Profissional não encontrado.")
        return self.repo.get_daily_agenda(professional_id, day)

    # Waitlist
    def join_waitlist(self, data: WaitlistCreate, actor: User, ip_address: str | None = None) -> WaitlistEntry:
        patient = self.patient_repo.get_by_id(data.patient_id)
        if not patient:
            raise NotFoundError("Paciente não encontrado.")
        if actor.role == UserRole.PACIENTE and patient.user_id != actor.id:
            raise ForbiddenError("Você só pode entrar na lista de espera para você mesmo.")

        professional = self.professional_repo.get_by_id(data.professional_id)
        if not professional:
            raise NotFoundError("Profissional não encontrado.")

        entry = WaitlistEntry(
            patient_id=data.patient_id,
            professional_id=data.professional_id,
            data_desejada=data.data_desejada,
            status=WaitlistStatus.AGUARDANDO,
        )
        self.repo.create_waitlist_entry(entry)
        self.db.commit()
        self.audit.log(actor.id, "WAITLIST_JOIN", "WaitlistEntry", entry.id, ip_address=ip_address)
        self.db.commit()
        return entry

    def _notify_waitlist(self, professional_id: int, day: date) -> list[WaitlistEntry]:
        """When a slot frees up, mark waiting entries for that professional/day as notified.
        In production this would trigger an email/SMS/push notification."""
        waiting = self.repo.get_waiting_for_professional_and_date(professional_id, day)
        notified = []
        for entry in waiting:
            entry.status = WaitlistStatus.NOTIFICADO
            entry.notified_at = datetime.now(timezone.utc)
            self.repo.update_waitlist_entry(entry)
            notified.append(entry)
        if notified:
            self.db.commit()
        return notified
