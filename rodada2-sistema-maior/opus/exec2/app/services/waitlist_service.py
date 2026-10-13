"""Lista de espera por horários ocupados."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.core import clock
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.pagination import PageParams, PageResult, SortParams
from app.models.appointment import WaitlistEntry
from app.models.enums import OPEN_WAITLIST_STATUSES, WaitlistStatus
from app.models.professional import Professional
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository, WaitlistRepository
from app.repositories.patient_repository import PatientRepository
from app.schemas.appointment import WaitlistCreate
from app.services import access, scheduling
from app.services.notification_service import NotificationService
from app.services.professional_service import ProfessionalService


class WaitlistService:
    def __init__(self, db: Session, notifications: NotificationService) -> None:
        self.db = db
        self.entries = WaitlistRepository(db)
        self.appointments = AppointmentRepository(db)
        self.patients = PatientRepository(db)
        self.professionals = ProfessionalService(db)
        self.notifications = notifications

    def get(self, actor: User, entry_id: int) -> WaitlistEntry:
        entry = self.entries.get(entry_id)
        if entry is None:
            raise NotFoundError("Registro da lista de espera não encontrado.")
        access.ensure_patient_scope(actor, entry.patient_id)
        return entry

    def join(self, actor: User, data: WaitlistCreate) -> WaitlistEntry:
        patient_id = access.own_patient_id(actor) if access.is_patient(actor) else data.patient_id
        if patient_id is None:
            raise BusinessRuleError("Informe o paciente ('patient_id').")
        access.ensure_patient_scope(actor, patient_id)
        patient = self.patients.get(patient_id)
        if patient is None:
            raise NotFoundError("Paciente não encontrado.")
        if not patient.is_active:
            raise BusinessRuleError("Paciente inativo.")

        professional = self.professionals.get_active_doctor(data.professional_id)
        if data.start_at <= clock.now():
            raise BusinessRuleError("Não é possível entrar na lista de espera de um horário passado.")
        slot = scheduling.resolve_slot(professional.availabilities, data.start_at)

        occupying = self.appointments.find_overlapping(slot.start_at, slot.end_at, professional_id=professional.id)
        if not occupying:
            raise BusinessRuleError(
                "Este horário está disponível; realize o agendamento diretamente.", code="horario_disponivel"
            )
        if any(appt.patient_id == patient.id for appt in occupying):
            raise ConflictError("O paciente já possui consulta neste horário com este médico.")
        if self.entries.find_open_overlapping(professional.id, slot.start_at, slot.end_at, patient_id=patient.id):
            raise ConflictError("O paciente já está na lista de espera para este horário.")

        entry = self.entries.add(
            WaitlistEntry(
                patient_id=patient.id,
                professional_id=professional.id,
                desired_start_at=slot.start_at,
                desired_end_at=slot.end_at,
                status=WaitlistStatus.WAITING,
                notes=data.notes,
                created_by_id=actor.id,
            )
        )
        self.db.commit()
        return entry

    def cancel(self, actor: User, entry_id: int) -> WaitlistEntry:
        entry = self.get(actor, entry_id)
        if entry.status not in OPEN_WAITLIST_STATUSES:
            raise BusinessRuleError("Somente registros ativos da lista de espera podem ser cancelados.")
        entry.status = WaitlistStatus.CANCELLED
        self.db.commit()
        return entry

    def search(
        self,
        actor: User,
        page: PageParams,
        sort: SortParams,
        *,
        patient_id: int | None,
        professional_id: int | None,
        status: WaitlistStatus | None,
    ) -> PageResult[WaitlistEntry]:
        self.entries.expire_past_entries(clock.now())
        self.db.commit()
        if access.is_patient(actor):
            patient_id = access.own_patient_id(actor)
        return self.entries.search(page, sort, patient_id=patient_id, professional_id=professional_id, status=status)

    # ------------------------------------------------------------------ integração com agendamento
    def notify_slot_released(self, professional: Professional, start: datetime, end: datetime) -> int:
        """Notifica (em ordem de chegada) os pacientes aguardando um horário que acabou de vagar.

        Não faz commit: participa da transação de quem liberou o horário.
        """
        if start <= clock.now():
            return 0
        waiting = self.entries.find_open_overlapping(professional.id, start, end)
        when = start.strftime("%d/%m/%Y às %H:%M")
        for position, entry in enumerate(waiting, start=1):
            self.notifications.notify_patient(
                entry.patient,
                "Horário disponível",
                f"O horário de {when} com {professional.full_name} ficou disponível. "
                f"Você é o {position}º da lista de espera; agende o quanto antes para garantir a vaga.",
            )
            entry.status = WaitlistStatus.NOTIFIED
            entry.notified_at = clock.now()
        return len(waiting)

    def mark_booked(self, patient_id: int, professional_id: int, start: datetime, end: datetime) -> None:
        for entry in self.entries.find_open_overlapping(professional_id, start, end, patient_id=patient_id):
            entry.status = WaitlistStatus.BOOKED
