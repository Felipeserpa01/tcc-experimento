"""Atendimento: prontuário, prescrições, exames e histórico clínico."""

from datetime import date
from pathlib import Path
from typing import BinaryIO

from sqlalchemy.orm import Session

from app.core import clock
from app.core.exceptions import BusinessRuleError, ConflictError, InvalidInputError, NotFoundError
from app.models.appointment import Appointment
from app.models.clinical import ExamRequest, MedicalRecord, Prescription
from app.models.enums import AppointmentStatus, ExamStatus
from app.models.patient import Patient
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.clinical_repository import (
    ExamRequestRepository,
    MedicalRecordRepository,
    PrescriptionRepository,
)
from app.repositories.patient_repository import PatientRepository
from app.schemas.clinical import (
    ExamRequestCreate,
    MedicalRecordCreate,
    MedicalRecordUpdate,
    PrescriptionCreate,
)
from app.services import access
from app.services.audit_service import AuditAction, AuditService
from app.services.file_storage import FileStorage

# Prontuário, prescrições e exames só podem ser registrados durante ou após o atendimento.
_ATTENDED_STATUSES = frozenset({AppointmentStatus.IN_PROGRESS, AppointmentStatus.COMPLETED})


class ClinicalService:
    def __init__(self, db: Session, storage: FileStorage | None = None) -> None:
        self.db = db
        self.appointments = AppointmentRepository(db)
        self.patients = PatientRepository(db)
        self.records = MedicalRecordRepository(db)
        self.prescriptions = PrescriptionRepository(db)
        self.exams = ExamRequestRepository(db)
        self.storage = storage or FileStorage()
        self.audit = AuditService(db)

    # ------------------------------------------------------------------ helpers
    def _get_appointment(self, appointment_id: int) -> Appointment:
        appointment = self.appointments.get(appointment_id)
        if appointment is None:
            raise NotFoundError("Consulta não encontrada.")
        return appointment

    def _appointment_for_writing(self, actor: User, appointment_id: int) -> Appointment:
        appointment = self._get_appointment(appointment_id)
        access.ensure_responsible_doctor(actor, appointment)
        if appointment.status not in _ATTENDED_STATUSES:
            raise BusinessRuleError(
                "Registros clínicos só podem ser feitos em consultas em andamento ou realizadas.",
                details={"status_atual": appointment.status.value},
            )
        return appointment

    def _appointment_for_reading(self, actor: User, appointment_id: int) -> Appointment:
        appointment = self._get_appointment(appointment_id)
        access.ensure_appointment_scope(actor, appointment)
        return appointment

    # ------------------------------------------------------------------ prontuário
    def create_record(self, actor: User, appointment_id: int, data: MedicalRecordCreate) -> MedicalRecord:
        appointment = self._appointment_for_writing(actor, appointment_id)
        if self.records.get_by_appointment(appointment.id) is not None:
            raise ConflictError("Esta consulta já possui prontuário registrado. Utilize a atualização (PATCH).")
        record = self.records.add(
            MedicalRecord(
                appointment_id=appointment.id,
                patient_id=appointment.patient_id,
                professional_id=appointment.professional_id,
                **data.model_dump(),
            )
        )
        self.audit.log(
            AuditAction.MEDICAL_RECORD_CREATED,
            actor=actor,
            entity_type="prontuario",
            entity_id=record.id,
            details={"consulta_id": appointment.id, "paciente_id": appointment.patient_id},
        )
        self.db.commit()
        return record

    def update_record(self, actor: User, appointment_id: int, data: MedicalRecordUpdate) -> MedicalRecord:
        appointment = self._appointment_for_writing(actor, appointment_id)
        record = self.records.get_by_appointment(appointment.id)
        if record is None:
            raise NotFoundError("Prontuário não encontrado para esta consulta.")
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            raise BusinessRuleError("Nenhum campo informado para atualização.")
        for field, value in changes.items():
            setattr(record, field, value)
        self.audit.log(
            AuditAction.MEDICAL_RECORD_UPDATED,
            actor=actor,
            entity_type="prontuario",
            entity_id=record.id,
            details={"consulta_id": appointment.id, "campos": sorted(changes)},
        )
        self.db.commit()
        return record

    def get_record(self, actor: User, appointment_id: int) -> MedicalRecord:
        appointment = self._appointment_for_reading(actor, appointment_id)
        record = self.records.get_by_appointment(appointment.id)
        if record is None:
            raise NotFoundError("Prontuário não encontrado para esta consulta.")
        self.audit.log(
            AuditAction.MEDICAL_RECORD_VIEWED,
            actor=actor,
            entity_type="prontuario",
            entity_id=record.id,
            details={"paciente_id": appointment.patient_id},
        )
        self.db.commit()
        return record

    # ------------------------------------------------------------------ prescrições
    def add_prescriptions(self, actor: User, appointment_id: int, data: PrescriptionCreate) -> list[Prescription]:
        appointment = self._appointment_for_writing(actor, appointment_id)
        created = self.prescriptions.add_all(
            [
                Prescription(
                    appointment_id=appointment.id,
                    patient_id=appointment.patient_id,
                    professional_id=appointment.professional_id,
                    **item.model_dump(),
                )
                for item in data.items
            ]
        )
        self.audit.log(
            AuditAction.PRESCRIPTION_CREATED,
            actor=actor,
            entity_type="consulta",
            entity_id=appointment.id,
            details={"prescricoes": [p.id for p in created]},
        )
        self.db.commit()
        return created

    def list_prescriptions(self, actor: User, appointment_id: int) -> list[Prescription]:
        appointment = self._appointment_for_reading(actor, appointment_id)
        return self.prescriptions.list_by_appointment(appointment.id)

    # ------------------------------------------------------------------ exames
    def request_exams(self, actor: User, appointment_id: int, data: ExamRequestCreate) -> list[ExamRequest]:
        appointment = self._appointment_for_writing(actor, appointment_id)
        created = self.exams.add_all(
            [
                ExamRequest(
                    appointment_id=appointment.id,
                    patient_id=appointment.patient_id,
                    professional_id=appointment.professional_id,
                    status=ExamStatus.REQUESTED,
                    **item.model_dump(),
                )
                for item in data.exams
            ]
        )
        self.audit.log(
            AuditAction.EXAM_REQUESTED,
            actor=actor,
            entity_type="consulta",
            entity_id=appointment.id,
            details={"exames": [e.id for e in created]},
        )
        self.db.commit()
        return created

    def list_exams(self, actor: User, appointment_id: int) -> list[ExamRequest]:
        appointment = self._appointment_for_reading(actor, appointment_id)
        return self.exams.list_by_appointment(appointment.id)

    def get_exam(self, actor: User, exam_id: int) -> ExamRequest:
        exam = self.exams.get(exam_id)
        if exam is None:
            raise NotFoundError("Exame não encontrado.")
        access.ensure_patient_scope(actor, exam.patient_id)
        return exam

    def attach_result(
        self,
        actor: User,
        exam_id: int,
        *,
        result_text: str | None,
        file: BinaryIO | None,
        filename: str | None,
        content_type: str | None,
    ) -> ExamRequest:
        exam = self.get_exam(actor, exam_id)
        access.ensure_responsible_doctor(actor, exam.appointment)
        if exam.status == ExamStatus.CANCELLED:
            raise BusinessRuleError("Não é possível anexar resultado a um exame cancelado.")
        if exam.status == ExamStatus.RESULT_AVAILABLE:
            raise ConflictError("Este exame já possui resultado registrado.")
        text = (result_text or "").strip() or None
        if text is None and file is None:
            raise InvalidInputError("Informe o texto do resultado e/ou um arquivo anexo.")
        if text is not None and len(text) > 10000:
            raise InvalidInputError("O texto do resultado deve ter no máximo 10000 caracteres.")

        stored = self.storage.save(file, filename, content_type, folder="exames") if file is not None else None
        exam.result_text = text
        if stored is not None:
            exam.result_file_path = stored.relative_path
            exam.result_file_name = stored.original_name
            exam.result_content_type = stored.content_type
        exam.status = ExamStatus.RESULT_AVAILABLE
        exam.result_registered_at = clock.now()
        self.audit.log(
            AuditAction.EXAM_RESULT_ATTACHED,
            actor=actor,
            entity_type="exame",
            entity_id=exam.id,
            details={"arquivo": stored is not None},
        )
        try:
            self.db.commit()
        except Exception:
            if stored is not None:
                self.storage.delete(stored.relative_path)
            raise
        return exam

    def result_file(self, actor: User, exam_id: int) -> tuple[Path, ExamRequest]:
        exam = self.get_exam(actor, exam_id)
        if not exam.result_file_path:
            raise NotFoundError("Este exame não possui arquivo de resultado.")
        path = self.storage.resolve(exam.result_file_path)
        self.audit.log(
            AuditAction.EXAM_RESULT_DOWNLOADED,
            actor=actor,
            entity_type="exame",
            entity_id=exam.id,
            details={"paciente_id": exam.patient_id},
        )
        self.db.commit()
        return path, exam

    def cancel_exam(self, actor: User, exam_id: int) -> ExamRequest:
        exam = self.get_exam(actor, exam_id)
        access.ensure_responsible_doctor(actor, exam.appointment)
        if exam.status != ExamStatus.REQUESTED:
            raise BusinessRuleError("Somente exames com status 'solicitado' podem ser cancelados.")
        exam.status = ExamStatus.CANCELLED
        exam.cancelled_at = clock.now()
        self.audit.log(AuditAction.EXAM_CANCELLED, actor=actor, entity_type="exame", entity_id=exam.id)
        self.db.commit()
        return exam

    # ------------------------------------------------------------------ histórico clínico
    def clinical_history(
        self, actor: User, patient_id: int, date_from: date | None = None, date_to: date | None = None
    ) -> tuple[Patient, list[Appointment]]:
        """Histórico completo em ordem cronológica: consultas com prontuário, prescrições e exames."""
        if date_from and date_to and date_from > date_to:
            raise InvalidInputError("'date_from' deve ser anterior ou igual a 'date_to'.")
        patient = self.patients.get(patient_id)
        if patient is None:
            raise NotFoundError("Paciente não encontrado.")
        access.ensure_patient_scope(actor, patient.id)
        appointments = self.appointments.list_for_patient(patient.id, date_from, date_to)
        self.audit.log(
            AuditAction.CLINICAL_HISTORY_VIEWED,
            actor=actor,
            entity_type="paciente",
            entity_id=patient.id,
        )
        self.db.commit()
        return patient, appointments
