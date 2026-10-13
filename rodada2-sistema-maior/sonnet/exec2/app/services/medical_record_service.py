"""Medical record, prescription and exam business logic."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.enums import ExamStatus, UserRole
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.medical_record import Exam, MedicalRecord, Prescription
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.medical_record_repository import MedicalRecordRepository
from app.repositories.professional_repository import ProfessionalRepository
from app.schemas.medical_record import ExamCreate, MedicalRecordCreate, PrescriptionCreate
from app.services.audit_service import AuditService


class MedicalRecordService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = MedicalRecordRepository(db)
        self.appointment_repo = AppointmentRepository(db)
        self.professional_repo = ProfessionalRepository(db)
        self.audit = AuditService(db)

    def _get_appointment_or_404(self, appointment_id: int):
        appointment = self.appointment_repo.get_by_id(appointment_id)
        if not appointment:
            raise NotFoundError("Consulta não encontrada.")
        return appointment

    def _ensure_is_responsible_doctor(self, appointment, actor: User) -> None:
        if actor.role != UserRole.MEDICO:
            raise ForbiddenError("Apenas o médico responsável pela consulta pode executar esta ação.")
        professional = self.professional_repo.get_by_user_id(actor.id)
        if not professional or professional.id != appointment.professional_id:
            raise ForbiddenError("Apenas o médico responsável pela consulta pode executar esta ação.")

    def _ensure_can_view(self, appointment, actor: User) -> None:
        if actor.role == UserRole.PACIENTE and appointment.patient.user_id != actor.id:
            raise ForbiddenError("Você só pode visualizar seus próprios dados clínicos.")

    def create_medical_record(
        self, appointment_id: int, data: MedicalRecordCreate, actor: User, ip_address: str | None = None
    ) -> MedicalRecord:
        appointment = self._get_appointment_or_404(appointment_id)
        self._ensure_is_responsible_doctor(appointment, actor)

        if self.repo.get_by_appointment_id(appointment_id):
            raise ConflictError("Já existe um prontuário registrado para esta consulta.")

        record = MedicalRecord(
            appointment_id=appointment_id,
            queixa=data.queixa,
            diagnostico=data.diagnostico,
            observacoes=data.observacoes,
            created_by=actor.id,
        )
        self.repo.create(record)
        self.db.commit()
        self.audit.log(actor.id, "MEDICAL_RECORD_CREATE", "MedicalRecord", record.id, ip_address=ip_address)
        self.db.commit()
        return record

    def get_medical_record(self, appointment_id: int, actor: User) -> MedicalRecord:
        appointment = self._get_appointment_or_404(appointment_id)
        self._ensure_can_view(appointment, actor)
        record = self.repo.get_by_appointment_id(appointment_id)
        if not record:
            raise NotFoundError("Prontuário não encontrado para esta consulta.")
        return record

    def add_prescription(
        self, appointment_id: int, data: PrescriptionCreate, actor: User, ip_address: str | None = None
    ) -> Prescription:
        appointment = self._get_appointment_or_404(appointment_id)
        self._ensure_is_responsible_doctor(appointment, actor)

        prescription = Prescription(
            appointment_id=appointment_id,
            created_by=actor.id,
            **data.model_dump(),
        )
        self.repo.create_prescription(prescription)
        self.db.commit()
        self.audit.log(actor.id, "PRESCRIPTION_CREATE", "Prescription", prescription.id, ip_address=ip_address)
        self.db.commit()
        return prescription

    def get_prescriptions(self, appointment_id: int, actor: User) -> list[Prescription]:
        appointment = self._get_appointment_or_404(appointment_id)
        self._ensure_can_view(appointment, actor)
        return self.repo.get_prescriptions_by_appointment(appointment_id)

    def add_exam(
        self, appointment_id: int, data: ExamCreate, actor: User, ip_address: str | None = None
    ) -> Exam:
        appointment = self._get_appointment_or_404(appointment_id)
        self._ensure_is_responsible_doctor(appointment, actor)

        exam = Exam(
            appointment_id=appointment_id,
            tipo_exame=data.tipo_exame,
            solicitado_por=actor.id,
        )
        self.repo.create_exam(exam)
        self.db.commit()
        self.audit.log(actor.id, "EXAM_CREATE", "Exam", exam.id, ip_address=ip_address)
        self.db.commit()
        return exam

    def attach_exam_result(
        self, exam_id: int, resultado: str, actor: User, ip_address: str | None = None
    ) -> Exam:
        exam = self.repo.get_exam_by_id(exam_id)
        if not exam:
            raise NotFoundError("Exame não encontrado.")

        appointment = self._get_appointment_or_404(exam.appointment_id)
        self._ensure_is_responsible_doctor(appointment, actor)

        exam.resultado = resultado
        exam.status = ExamStatus.RESULTADO_DISPONIVEL
        exam.resultado_anexado_em = datetime.now(timezone.utc)
        self.repo.update_exam(exam)
        self.db.commit()
        self.audit.log(actor.id, "EXAM_RESULT_ATTACHED", "Exam", exam.id, ip_address=ip_address)
        self.db.commit()
        return exam

    def get_exams(self, appointment_id: int, actor: User) -> list[Exam]:
        appointment = self._get_appointment_or_404(appointment_id)
        self._ensure_can_view(appointment, actor)
        return self.repo.get_exams_by_appointment(appointment_id)

    def get_patient_history(self, patient_id: int, actor: User) -> list[dict]:
        patient = self.repo.get_patient_by_id(patient_id)
        if not patient:
            raise NotFoundError("Paciente não encontrado.")

        if actor.role == UserRole.PACIENTE and patient.user_id != actor.id:
            raise ForbiddenError("Você só pode visualizar o seu próprio histórico clínico.")

        appointments = self.repo.get_patient_history(patient_id)
        history = []
        for appt in appointments:
            record = self.repo.get_by_appointment_id(appt.id)
            prescriptions = self.repo.get_prescriptions_by_appointment(appt.id)
            exams = self.repo.get_exams_by_appointment(appt.id)
            history.append(
                {
                    "appointment_id": appt.id,
                    "data_hora": appt.data_hora,
                    "status": appt.status.value,
                    "professional_id": appt.professional_id,
                    "medical_record": (
                        {
                            "queixa": record.queixa,
                            "diagnostico": record.diagnostico,
                            "observacoes": record.observacoes,
                        }
                        if record
                        else None
                    ),
                    "prescriptions": [
                        {
                            "medicamento": p.medicamento,
                            "dosagem": p.dosagem,
                            "frequencia": p.frequencia,
                            "duracao": p.duracao,
                        }
                        for p in prescriptions
                    ],
                    "exams": [
                        {
                            "tipo_exame": e.tipo_exame,
                            "status": e.status.value,
                            "resultado": e.resultado,
                        }
                        for e in exams
                    ],
                }
            )
        return history
