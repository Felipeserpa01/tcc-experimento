from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app.models.appointment import Appointment, WaitListEntry
from app.models.enums import AppointmentStatus, UserRole
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.professional_repository import ProfessionalRepository
from app.schemas.appointment import AppointmentCreate, WaitListCreate
from app.services.audit_service import AuditService

ACTIVE_STATUSES = {
    AppointmentStatus.SCHEDULED,
    AppointmentStatus.CONFIRMED,
    AppointmentStatus.IN_PROGRESS,
}

VALID_TRANSITIONS: dict[AppointmentStatus, set[AppointmentStatus]] = {
    AppointmentStatus.SCHEDULED: {
        AppointmentStatus.CONFIRMED,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.NO_SHOW,
    },
    AppointmentStatus.CONFIRMED: {
        AppointmentStatus.IN_PROGRESS,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.NO_SHOW,
    },
    AppointmentStatus.IN_PROGRESS: {AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED},
    AppointmentStatus.COMPLETED: set(),
    AppointmentStatus.CANCELLED: set(),
    AppointmentStatus.NO_SHOW: set(),
}


class AppointmentService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = AppointmentRepository(db)
        self.patients = PatientRepository(db)
        self.professionals = ProfessionalRepository(db)
        self.audit = AuditService(db)

    def schedule(
        self, payload: AppointmentCreate, acting_user: User, ip_address: str | None = None
    ) -> Appointment:
        patient = self.patients.get_by_id(payload.patient_id)
        if patient is None:
            raise NotFoundError("Paciente não encontrado.")

        if acting_user.role == UserRole.PATIENT and patient.user_id != acting_user.id:
            raise ForbiddenError("Pacientes só podem agendar consultas para si mesmos.")

        doctor = self.professionals.get_by_id(payload.doctor_id)
        if doctor is None:
            raise NotFoundError("Profissional não encontrado.")

        scheduled_at = _ensure_timezone(payload.scheduled_at)
        now = datetime.now(timezone.utc)
        if scheduled_at <= now:
            raise ValidationAppError("Não é possível agendar consulta em data ou horário passado.")

        self._validate_within_availability(payload.doctor_id, scheduled_at, payload.duration_minutes)

        end = scheduled_at + timedelta(minutes=payload.duration_minutes)
        conflict = self.repository.find_conflicting(payload.doctor_id, scheduled_at, end)
        if conflict is not None:
            raise ConflictError("O profissional já possui uma consulta agendada neste horário.")

        appointment = Appointment(
            patient_id=payload.patient_id,
            doctor_id=payload.doctor_id,
            scheduled_at=scheduled_at,
            duration_minutes=payload.duration_minutes,
        )
        created = self.repository.create(appointment)
        self.audit.log(
            acting_user.id, "CREATE_APPOINTMENT", "Appointment", created.id, ip_address=ip_address
        )
        return created

    def _validate_within_availability(self, doctor_id: int, scheduled_at: datetime, duration: int) -> None:
        availabilities = self.professionals.get_availabilities(doctor_id)
        if not availabilities:
            raise ValidationAppError("Profissional não possui agenda de disponibilidade cadastrada.")

        weekday = scheduled_at.weekday()
        slot_start = scheduled_at.time()
        slot_end = (scheduled_at + timedelta(minutes=duration)).time()

        for slot in availabilities:
            if slot.weekday != weekday:
                continue
            if slot_start >= slot.start_time and slot_end <= slot.end_time:
                return

        raise ValidationAppError("Horário fora da agenda de disponibilidade do profissional.")

    def get_appointment(self, appointment_id: int, acting_user: User) -> Appointment:
        appointment = self.repository.get_by_id(appointment_id)
        if appointment is None:
            raise NotFoundError("Consulta não encontrada.")
        self._authorize_view(appointment, acting_user)
        return appointment

    def _authorize_view(self, appointment: Appointment, acting_user: User) -> None:
        if acting_user.role in {UserRole.ADMIN, UserRole.RECEPTIONIST, UserRole.NURSE}:
            return
        if acting_user.role == UserRole.DOCTOR and appointment.doctor.user_id == acting_user.id:
            return
        if acting_user.role == UserRole.PATIENT and appointment.patient.user_id == acting_user.id:
            return
        raise ForbiddenError("Você não tem permissão para acessar esta consulta.")

    def search(
        self,
        patient_id: int | None,
        doctor_id: int | None,
        status: AppointmentStatus | None,
        start: datetime | None,
        end: datetime | None,
        acting_user: User,
        offset: int,
        limit: int,
    ) -> tuple[list[Appointment], int]:
        if acting_user.role == UserRole.PATIENT:
            own_patient = self.patients.get_by_user_id(acting_user.id)
            patient_id = own_patient.id if own_patient else -1
        elif acting_user.role == UserRole.DOCTOR:
            own_professional = self.professionals.get_by_user_id(acting_user.id)
            doctor_id = own_professional.id if own_professional else -1

        return self.repository.search(patient_id, doctor_id, status, start, end, offset, limit)

    def confirm(self, appointment_id: int, acting_user: User, ip_address: str | None = None) -> Appointment:
        appointment = self._get_and_authorize_manage(appointment_id, acting_user)
        self._transition(appointment, AppointmentStatus.CONFIRMED)
        updated = self.repository.update(appointment)
        self.audit.log(acting_user.id, "CONFIRM_APPOINTMENT", "Appointment", appointment_id, ip_address=ip_address)
        return updated

    def cancel(
        self, appointment_id: int, reason: str, acting_user: User, ip_address: str | None = None
    ) -> Appointment:
        appointment = self._get_and_authorize_manage(appointment_id, acting_user)
        self._transition(appointment, AppointmentStatus.CANCELLED)
        appointment.cancellation_reason = reason
        updated = self.repository.update(appointment)
        self.audit.log(acting_user.id, "CANCEL_APPOINTMENT", "Appointment", appointment_id, ip_address=ip_address)
        self._notify_waitlist(appointment.doctor_id, appointment.scheduled_at.date())
        return updated

    def reschedule(
        self, appointment_id: int, new_scheduled_at: datetime, acting_user: User, ip_address: str | None = None
    ) -> Appointment:
        appointment = self._get_and_authorize_manage(appointment_id, acting_user)
        if appointment.status not in ACTIVE_STATUSES:
            raise ConflictError("Somente consultas ativas podem ser remarcadas.")

        new_scheduled_at = _ensure_timezone(new_scheduled_at)
        now = datetime.now(timezone.utc)
        if new_scheduled_at <= now:
            raise ValidationAppError("Não é possível remarcar para uma data ou horário passado.")

        self._validate_within_availability(appointment.doctor_id, new_scheduled_at, appointment.duration_minutes)

        end = new_scheduled_at + timedelta(minutes=appointment.duration_minutes)
        conflict = self.repository.find_conflicting(
            appointment.doctor_id, new_scheduled_at, end, exclude_id=appointment.id
        )
        if conflict is not None:
            raise ConflictError("O profissional já possui uma consulta agendada neste horário.")

        appointment.scheduled_at = new_scheduled_at
        appointment.status = AppointmentStatus.SCHEDULED
        updated = self.repository.update(appointment)
        self.audit.log(acting_user.id, "RESCHEDULE_APPOINTMENT", "Appointment", appointment_id, ip_address=ip_address)
        return updated

    def update_status(
        self, appointment_id: int, new_status: AppointmentStatus, acting_user: User, ip_address: str | None = None
    ) -> Appointment:
        appointment = self._get_and_authorize_manage(appointment_id, acting_user)
        self._transition(appointment, new_status)
        updated = self.repository.update(appointment)
        self.audit.log(
            acting_user.id, f"UPDATE_APPOINTMENT_STATUS_{new_status.value}", "Appointment", appointment_id, ip_address=ip_address
        )
        return updated

    def _transition(self, appointment: Appointment, new_status: AppointmentStatus) -> None:
        allowed = VALID_TRANSITIONS.get(appointment.status, set())
        if new_status not in allowed:
            raise ConflictError(
                f"Não é possível alterar o status de '{appointment.status.value}' para '{new_status.value}'."
            )
        appointment.status = new_status

    def _get_and_authorize_manage(self, appointment_id: int, acting_user: User) -> Appointment:
        appointment = self.repository.get_by_id(appointment_id)
        if appointment is None:
            raise NotFoundError("Consulta não encontrada.")

        if acting_user.role in {UserRole.ADMIN, UserRole.RECEPTIONIST, UserRole.NURSE}:
            return appointment
        if acting_user.role == UserRole.DOCTOR and appointment.doctor.user_id == acting_user.id:
            return appointment
        if acting_user.role == UserRole.PATIENT and appointment.patient.user_id == acting_user.id:
            return appointment

        raise ForbiddenError("Você não tem permissão para gerenciar esta consulta.")

    def get_doctor_day_agenda(self, doctor_id: int, day: date, acting_user: User) -> list[Appointment]:
        if acting_user.role == UserRole.DOCTOR:
            own_professional = self.professionals.get_by_user_id(acting_user.id)
            if own_professional is None or own_professional.id != doctor_id:
                raise ForbiddenError("Você só pode visualizar sua própria agenda.")
        return self.repository.get_doctor_day_agenda(doctor_id, day)

    def join_waitlist(self, payload: WaitListCreate, acting_user: User) -> WaitListEntry:
        patient = self.patients.get_by_id(payload.patient_id)
        if patient is None:
            raise NotFoundError("Paciente não encontrado.")
        if acting_user.role == UserRole.PATIENT and patient.user_id != acting_user.id:
            raise ForbiddenError("Pacientes só podem entrar na lista de espera para si mesmos.")

        doctor = self.professionals.get_by_id(payload.doctor_id)
        if doctor is None:
            raise NotFoundError("Profissional não encontrado.")

        entry = WaitListEntry(
            patient_id=payload.patient_id, doctor_id=payload.doctor_id, desired_date=payload.desired_date
        )
        return self.repository.add_waitlist_entry(entry)

    def list_waitlist(self, offset: int, limit: int) -> tuple[list[WaitListEntry], int]:
        return self.repository.list_waitlist(offset, limit)

    def _notify_waitlist(self, doctor_id: int, freed_date: date) -> None:
        """Marks waiting patients as notified when a slot on that date frees up."""
        entries = self.repository.get_waitlist_for_doctor(doctor_id, freed_date)
        for entry in entries:
            entry.notified = True
        if entries:
            self.db.commit()


def _ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
