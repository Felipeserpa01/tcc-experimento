"""Prontuario, prescricoes, exames, anexos e historico clinico."""

from __future__ import annotations

import re
import unicodedata
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.datetime_utils import now
from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    PayloadTooLargeError,
    PermissionDeniedError,
    UnsupportedMediaTypeError,
)
from app.core.pagination import PaginationParams
from app.models.appointment import Appointment
from app.models.enums import (
    STAFF_ROLES,
    AppointmentStatus,
    ExamStatus,
    NotificationType,
    UserRole,
)
from app.models.medical_record import ExamAttachment, ExamRequest, MedicalRecord, Prescription
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.medical_record_repository import (
    ExamAttachmentRepository,
    ExamRepository,
    MedicalRecordRepository,
    PrescriptionRepository,
)
from app.repositories.patient_repository import PatientRepository
from app.repositories.professional_repository import ProfessionalRepository
from app.schemas.medical_record import (
    ExamRequestCreate,
    ExamResultCreate,
    ExamStatusUpdate,
    MedicalRecordCreate,
    MedicalRecordUpdate,
    PrescriptionCreate,
    PrescriptionUpdate,
)
from app.services.audit_service import AuditAction, AuditService
from app.services.notification_service import NotificationService

settings = get_settings()

#: Status em que a consulta aceita registro clinico.
CLINICAL_WRITE_STATUSES = frozenset({AppointmentStatus.IN_PROGRESS, AppointmentStatus.COMPLETED})

_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(filename: str) -> str:
    """Remove acentos e caracteres perigosos (evita path traversal)."""
    base = Path(filename or "arquivo").name
    normalized = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode("ascii")
    cleaned = _SAFE_FILENAME_RE.sub("_", normalized).strip("._-")
    return cleaned or "arquivo"


class MedicalRecordService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.records = MedicalRecordRepository(db)
        self.prescriptions = PrescriptionRepository(db)
        self.exams = ExamRepository(db)
        self.attachments = ExamAttachmentRepository(db)
        self.appointments = AppointmentRepository(db)
        self.patients = PatientRepository(db)
        self.professionals = ProfessionalRepository(db)
        self.notifications = NotificationService(db)
        self.audit = AuditService(db)

    # ==================================================================
    # Autorizacao
    # ==================================================================
    def _get_appointment(self, appointment_id: int) -> Appointment:
        appointment = self.appointments.get(appointment_id)
        if appointment is None:
            raise NotFoundError(f"Consulta {appointment_id} nao encontrada.")
        return appointment

    def ensure_responsible_doctor(self, actor: User, appointment: Appointment) -> None:
        """Somente o medico responsavel registra prontuario, prescricao e exames."""
        if actor.role != UserRole.DOCTOR:
            raise PermissionDeniedError(
                "Apenas o medico responsavel pela consulta pode registrar dados clinicos."
            )
        professional = self.professionals.get_by_user_id(actor.id)
        if professional is None or professional.id != appointment.professional_id:
            raise PermissionDeniedError(
                "Somente o medico responsavel por esta consulta pode registrar dados clinicos."
            )

    def ensure_can_read_patient_data(self, actor: User, patient_id: int) -> None:
        """Equipe le tudo; paciente le apenas o proprio prontuario."""
        if actor.role in STAFF_ROLES:
            return
        if actor.role == UserRole.PATIENT:
            own = self.patients.get_by_user_id(actor.id)
            if own is not None and own.id == patient_id:
                return
        raise PermissionDeniedError("Voce so pode visualizar o proprio prontuario.")

    @staticmethod
    def _ensure_appointment_ready(appointment: Appointment) -> None:
        if appointment.status not in CLINICAL_WRITE_STATUSES:
            raise BusinessRuleError(
                "O registro clinico so e permitido em consultas iniciadas ou realizadas. "
                f"Status atual: '{appointment.status.value}'.",
            )

    # ==================================================================
    # Prontuario
    # ==================================================================
    def create_record(
        self, appointment_id: int, payload: MedicalRecordCreate, actor: User
    ) -> MedicalRecord:
        appointment = self._get_appointment(appointment_id)
        self.ensure_responsible_doctor(actor, appointment)
        self._ensure_appointment_ready(appointment)

        if self.records.get_by_appointment(appointment.id) is not None:
            raise ConflictError("Esta consulta ja possui prontuario registrado.")

        record = MedicalRecord(
            appointment_id=appointment.id,
            patient_id=appointment.patient_id,
            professional_id=appointment.professional_id,
            **payload.model_dump(),
        )
        self.db.add(record)
        self.db.flush()

        # Prescricoes e exames criados antes do prontuario passam a referencia-lo.
        for prescription in self.prescriptions.list_for_appointment(appointment.id):
            if prescription.medical_record_id is None:
                prescription.medical_record_id = record.id
        for exam in self.exams.list_for_appointment(appointment.id):
            if exam.medical_record_id is None:
                exam.medical_record_id = record.id
        self.db.flush()

        self.audit.record(
            action=AuditAction.MEDICAL_RECORD_CREATED,
            actor=actor,
            resource_type="medical_record",
            resource_id=record.id,
            description=f"Prontuario registrado para a consulta {appointment.id}.",
        )
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_record_by_appointment(self, appointment_id: int, actor: User) -> MedicalRecord:
        appointment = self._get_appointment(appointment_id)
        self.ensure_can_read_patient_data(actor, appointment.patient_id)
        record = self.records.get_by_appointment(appointment.id)
        if record is None:
            raise NotFoundError("Esta consulta ainda nao possui prontuario.")
        return record

    def get_record(self, record_id: int, actor: User) -> MedicalRecord:
        record = self.records.get(record_id)
        if record is None:
            raise NotFoundError(f"Prontuario {record_id} nao encontrado.")
        self.ensure_can_read_patient_data(actor, record.patient_id)
        return record

    def update_record(
        self, record_id: int, payload: MedicalRecordUpdate, actor: User
    ) -> MedicalRecord:
        record = self.records.get(record_id)
        if record is None:
            raise NotFoundError(f"Prontuario {record_id} nao encontrado.")
        appointment = self._get_appointment(record.appointment_id)
        self.ensure_responsible_doctor(actor, appointment)

        data = payload.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(record, field, value)
        self.db.flush()

        self.audit.record(
            action=AuditAction.MEDICAL_RECORD_UPDATED,
            actor=actor,
            resource_type="medical_record",
            resource_id=record.id,
            description="Prontuario atualizado.",
            extra={"fields": sorted(data.keys())},
        )
        self.db.commit()
        self.db.refresh(record)
        return record

    def search_records(
        self,
        pagination: PaginationParams,
        actor: User,
        *,
        patient_id: int | None = None,
        professional_id: int | None = None,
        start_date=None,
        end_date=None,
    ) -> tuple[list[MedicalRecord], int]:
        if actor.role == UserRole.PATIENT:
            own = self.patients.get_by_user_id(actor.id)
            if own is None:
                return [], 0
            patient_id = own.id
        return self.records.search(
            pagination,
            patient_id=patient_id,
            professional_id=professional_id,
            start_date=start_date,
            end_date=end_date,
        )

    # ==================================================================
    # Prescricoes
    # ==================================================================
    def create_prescription(
        self, appointment_id: int, payload: PrescriptionCreate, actor: User
    ) -> Prescription:
        appointment = self._get_appointment(appointment_id)
        self.ensure_responsible_doctor(actor, appointment)
        self._ensure_appointment_ready(appointment)

        record = self.records.get_by_appointment(appointment.id)
        prescription = Prescription(
            appointment_id=appointment.id,
            medical_record_id=record.id if record else None,
            patient_id=appointment.patient_id,
            professional_id=appointment.professional_id,
            **payload.model_dump(),
        )
        self.db.add(prescription)
        self.db.flush()

        self.audit.record(
            action=AuditAction.PRESCRIPTION_CREATED,
            actor=actor,
            resource_type="prescription",
            resource_id=prescription.id,
            description=(
                f"Prescricao de '{prescription.medication_name}' registrada "
                f"na consulta {appointment.id}."
            ),
        )
        self.db.commit()
        self.db.refresh(prescription)
        return prescription

    def list_prescriptions(self, appointment_id: int, actor: User) -> list[Prescription]:
        appointment = self._get_appointment(appointment_id)
        self.ensure_can_read_patient_data(actor, appointment.patient_id)
        return self.prescriptions.list_for_appointment(appointment.id)

    def update_prescription(
        self, prescription_id: int, payload: PrescriptionUpdate, actor: User
    ) -> Prescription:
        prescription = self.prescriptions.get(prescription_id)
        if prescription is None:
            raise NotFoundError(f"Prescricao {prescription_id} nao encontrada.")
        appointment = self._get_appointment(prescription.appointment_id)
        self.ensure_responsible_doctor(actor, appointment)

        data = payload.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(prescription, field, value)
        self.db.flush()

        self.audit.record(
            action=AuditAction.PRESCRIPTION_UPDATED,
            actor=actor,
            resource_type="prescription",
            resource_id=prescription.id,
            description="Prescricao atualizada.",
        )
        self.db.commit()
        self.db.refresh(prescription)
        return prescription

    def delete_prescription(self, prescription_id: int, actor: User) -> None:
        prescription = self.prescriptions.get(prescription_id)
        if prescription is None:
            raise NotFoundError(f"Prescricao {prescription_id} nao encontrada.")
        appointment = self._get_appointment(prescription.appointment_id)
        self.ensure_responsible_doctor(actor, appointment)

        self.db.delete(prescription)
        self.db.flush()
        self.audit.record(
            action=AuditAction.PRESCRIPTION_DELETED,
            actor=actor,
            resource_type="prescription",
            resource_id=prescription_id,
            description="Prescricao removida.",
        )
        self.db.commit()

    # ==================================================================
    # Exames
    # ==================================================================
    def create_exam(
        self, appointment_id: int, payload: ExamRequestCreate, actor: User
    ) -> ExamRequest:
        appointment = self._get_appointment(appointment_id)
        self.ensure_responsible_doctor(actor, appointment)
        self._ensure_appointment_ready(appointment)

        record = self.records.get_by_appointment(appointment.id)
        exam = ExamRequest(
            appointment_id=appointment.id,
            medical_record_id=record.id if record else None,
            patient_id=appointment.patient_id,
            professional_id=appointment.professional_id,
            status=ExamStatus.REQUESTED,
            **payload.model_dump(),
        )
        self.db.add(exam)
        self.db.flush()

        self.audit.record(
            action=AuditAction.EXAM_REQUESTED,
            actor=actor,
            resource_type="exam_request",
            resource_id=exam.id,
            description=f"Exame '{exam.exam_name}' solicitado na consulta {appointment.id}.",
        )
        self.db.commit()
        self.db.refresh(exam)
        return exam

    def get_exam(self, exam_id: int, actor: User) -> ExamRequest:
        exam = self.exams.get(exam_id)
        if exam is None:
            raise NotFoundError(f"Exame {exam_id} nao encontrado.")
        self.ensure_can_read_patient_data(actor, exam.patient_id)
        return exam

    def list_exams(self, appointment_id: int, actor: User) -> list[ExamRequest]:
        appointment = self._get_appointment(appointment_id)
        self.ensure_can_read_patient_data(actor, appointment.patient_id)
        return self.exams.list_for_appointment(appointment.id)

    def update_exam_status(
        self, exam_id: int, payload: ExamStatusUpdate, actor: User
    ) -> ExamRequest:
        exam = self.exams.get(exam_id)
        if exam is None:
            raise NotFoundError(f"Exame {exam_id} nao encontrado.")
        appointment = self._get_appointment(exam.appointment_id)
        self.ensure_responsible_doctor(actor, appointment)

        if exam.status == ExamStatus.CANCELLED:
            raise ConflictError("Exame cancelado nao pode ser alterado.")
        if payload.status == ExamStatus.CANCELLED and not payload.cancellation_reason:
            raise BusinessRuleError("Informe o motivo do cancelamento do exame.")

        exam.status = payload.status
        if payload.status == ExamStatus.CANCELLED:
            exam.cancellation_reason = payload.cancellation_reason
        self.db.flush()

        self.audit.record(
            action=AuditAction.EXAM_UPDATED,
            actor=actor,
            resource_type="exam_request",
            resource_id=exam.id,
            description=f"Status do exame alterado para '{exam.status.value}'.",
        )
        self.db.commit()
        self.db.refresh(exam)
        return exam

    def register_exam_result(
        self, exam_id: int, payload: ExamResultCreate, actor: User
    ) -> ExamRequest:
        exam = self.exams.get(exam_id)
        if exam is None:
            raise NotFoundError(f"Exame {exam_id} nao encontrado.")
        appointment = self._get_appointment(exam.appointment_id)
        self.ensure_responsible_doctor(actor, appointment)

        if exam.status == ExamStatus.CANCELLED:
            raise ConflictError("Nao e possivel registrar resultado de exame cancelado.")

        exam.result_summary = payload.result_summary
        exam.result_notes = payload.result_notes
        exam.result_registered_at = now()
        exam.result_registered_by_id = actor.id
        exam.status = ExamStatus.COMPLETED
        self.db.flush()

        self.notifications.notify(
            user_id=exam.patient.user_id,
            notification_type=NotificationType.EXAM_RESULT_AVAILABLE,
            title="Resultado de exame disponivel",
            message=f"O resultado do exame '{exam.exam_name}' ja esta disponivel.",
            resource_type="exam_request",
            resource_id=exam.id,
        )
        self.audit.record(
            action=AuditAction.EXAM_RESULT_REGISTERED,
            actor=actor,
            resource_type="exam_request",
            resource_id=exam.id,
            description=f"Resultado do exame '{exam.exam_name}' registrado.",
        )
        self.db.commit()
        self.db.refresh(exam)
        return exam

    # ------------------------------------------------------------------
    # Anexos de resultado
    # ------------------------------------------------------------------
    def attach_exam_result(
        self,
        exam_id: int,
        *,
        filename: str,
        content: bytes,
        content_type: str | None,
        description: str | None,
        actor: User,
    ) -> ExamAttachment:
        exam = self.exams.get(exam_id)
        if exam is None:
            raise NotFoundError(f"Exame {exam_id} nao encontrado.")
        appointment = self._get_appointment(exam.appointment_id)
        self.ensure_responsible_doctor(actor, appointment)

        if exam.status == ExamStatus.CANCELLED:
            raise ConflictError("Nao e possivel anexar resultado a um exame cancelado.")
        if not content:
            raise BusinessRuleError("Arquivo vazio.")
        if len(content) > settings.max_upload_size_bytes:
            raise PayloadTooLargeError(
                f"Arquivo acima do limite de {settings.max_upload_size_mb} MB."
            )

        safe_name = sanitize_filename(filename)
        extension = Path(safe_name).suffix.lower()
        if extension not in settings.allowed_extensions:
            raise UnsupportedMediaTypeError(
                f"Extensao '{extension or 'desconhecida'}' nao permitida.",
                details={"allowed": sorted(settings.allowed_extensions)},
            )

        target_dir = settings.upload_path / "exams" / str(exam.id)
        target_dir.mkdir(parents=True, exist_ok=True)
        stored_name = f"{uuid.uuid4().hex}{extension}"
        stored_path = target_dir / stored_name
        stored_path.write_bytes(content)

        attachment = ExamAttachment(
            exam_id=exam.id,
            filename=safe_name,
            stored_path=str(stored_path),
            content_type=content_type,
            size_bytes=len(content),
            description=description,
            uploaded_by_id=actor.id,
        )
        self.db.add(attachment)
        if exam.status == ExamStatus.REQUESTED:
            exam.status = ExamStatus.COLLECTED
        self.db.flush()

        self.audit.record(
            action=AuditAction.EXAM_ATTACHMENT_ADDED,
            actor=actor,
            resource_type="exam_attachment",
            resource_id=attachment.id,
            description=f"Anexo '{safe_name}' adicionado ao exame {exam.id}.",
            extra={"size_bytes": len(content)},
        )
        self.db.commit()
        self.db.refresh(attachment)
        return attachment

    def list_attachments(self, exam_id: int, actor: User) -> list[ExamAttachment]:
        exam = self.get_exam(exam_id, actor)
        return self.attachments.list_for_exam(exam.id)

    def get_attachment_for_download(self, attachment_id: int, actor: User) -> ExamAttachment:
        attachment = self.attachments.get(attachment_id)
        if attachment is None:
            raise NotFoundError(f"Anexo {attachment_id} nao encontrado.")
        exam = self.exams.get(attachment.exam_id)
        if exam is None:
            raise NotFoundError("Exame do anexo nao encontrado.")
        self.ensure_can_read_patient_data(actor, exam.patient_id)

        if not Path(attachment.stored_path).is_file():
            raise NotFoundError("Arquivo do anexo nao esta mais disponivel no servidor.")

        self.audit.record(
            action=AuditAction.EXAM_ATTACHMENT_DOWNLOADED,
            actor=actor,
            resource_type="exam_attachment",
            resource_id=attachment.id,
            description=f"Download do anexo '{attachment.filename}'.",
        )
        self.db.commit()
        return attachment

    # ==================================================================
    # Historico clinico completo
    # ==================================================================
    def clinical_history(self, patient_id: int, actor: User) -> dict:
        patient = self.patients.get(patient_id)
        if patient is None:
            raise NotFoundError(f"Paciente {patient_id} nao encontrado.")
        self.ensure_can_read_patient_data(actor, patient.id)

        appointments = self.appointments.list_for_patient(patient.id)
        records = {
            record.appointment_id: record for record in self.records.list_for_patient(patient.id)
        }
        prescriptions: dict[int, list[Prescription]] = {}
        for prescription in self.prescriptions.list_for_patient(patient.id):
            prescriptions.setdefault(prescription.appointment_id, []).append(prescription)
        exams: dict[int, list[ExamRequest]] = {}
        for exam in self.exams.list_for_patient(patient.id):
            exams.setdefault(exam.appointment_id, []).append(exam)

        entries = []
        for appointment in appointments:
            entries.append(
                {
                    "appointment_id": appointment.id,
                    "scheduled_start": appointment.scheduled_start,
                    "status": appointment.status,
                    "professional_id": appointment.professional_id,
                    "professional_name": appointment.professional.full_name,
                    "specialty": appointment.professional.specialty,
                    "medical_record": records.get(appointment.id),
                    "prescriptions": prescriptions.get(appointment.id, []),
                    "exams": exams.get(appointment.id, []),
                }
            )

        self.audit.record(
            action=AuditAction.MEDICAL_RECORD_VIEWED,
            actor=actor,
            resource_type="patient",
            resource_id=patient.id,
            description=f"Historico clinico de '{patient.full_name}' consultado.",
        )
        self.db.commit()

        return {
            "patient_id": patient.id,
            "patient_name": patient.full_name,
            "total_appointments": len(entries),
            "entries": entries,
        }
