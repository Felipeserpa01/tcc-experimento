from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.enums import AppointmentStatus, UserRole
from app.models.medical_record import Exam, MedicalRecord, Prescription
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.medical_record_repository import MedicalRecordRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.professional_repository import ProfessionalRepository
from app.schemas.medical_record import ExamCreate, MedicalRecordCreate, PrescriptionCreate
from app.services.audit_service import AuditService


class MedicalRecordService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = MedicalRecordRepository(db)
        self.appointments = AppointmentRepository(db)
        self.patients = PatientRepository(db)
        self.professionals = ProfessionalRepository(db)
        self.audit = AuditService(db)

    def create_record(
        self, appointment_id: int, payload: MedicalRecordCreate, acting_user: User, ip_address: str | None = None
    ) -> MedicalRecord:
        appointment = self.appointments.get_by_id(appointment_id)
        if appointment is None:
            raise NotFoundError("Consulta não encontrada.")

        self._authorize_responsible_doctor(appointment, acting_user)

        if self.repository.get_by_appointment_id(appointment_id) is not None:
            raise ConflictError("Já existe um prontuário registrado para esta consulta.")

        if appointment.status not in {AppointmentStatus.IN_PROGRESS, AppointmentStatus.COMPLETED}:
            raise ConflictError("O prontuário só pode ser registrado para consultas em andamento ou realizadas.")

        record = MedicalRecord(appointment_id=appointment_id, **payload.model_dump())
        created = self.repository.create(record)

        appointment.status = AppointmentStatus.COMPLETED
        self.appointments.update(appointment)

        self.audit.log(acting_user.id, "CREATE_MEDICAL_RECORD", "MedicalRecord", created.id, ip_address=ip_address)
        return created

    def add_prescription(
        self, record_id: int, payload: PrescriptionCreate, acting_user: User, ip_address: str | None = None
    ) -> Prescription:
        record = self._get_record(record_id)
        self._authorize_responsible_doctor(record.appointment, acting_user)

        prescription = Prescription(medical_record_id=record_id, **payload.model_dump())
        created = self.repository.add_prescription(prescription)
        self.audit.log(acting_user.id, "CREATE_PRESCRIPTION", "Prescription", created.id, ip_address=ip_address)
        return created

    def add_exam(
        self, record_id: int, payload: ExamCreate, acting_user: User, ip_address: str | None = None
    ) -> Exam:
        record = self._get_record(record_id)
        self._authorize_responsible_doctor(record.appointment, acting_user)

        exam = Exam(medical_record_id=record_id, exam_name=payload.exam_name)
        created = self.repository.add_exam(exam)
        self.audit.log(acting_user.id, "CREATE_EXAM", "Exam", created.id, ip_address=ip_address)
        return created

    def attach_exam_result(
        self, exam_id: int, result: str, acting_user: User, ip_address: str | None = None
    ) -> Exam:
        exam = self.repository.get_exam_by_id(exam_id)
        if exam is None:
            raise NotFoundError("Exame não encontrado.")

        self._authorize_responsible_doctor(exam.medical_record.appointment, acting_user)

        exam.result = result
        exam.result_attached_at = datetime.now(timezone.utc)
        updated = self.repository.update_exam(exam)
        self.audit.log(acting_user.id, "ATTACH_EXAM_RESULT", "Exam", exam_id, ip_address=ip_address)
        return updated

    def get_record(self, record_id: int, acting_user: User) -> MedicalRecord:
        record = self._get_record(record_id)
        self._authorize_view(record, acting_user)
        return record

    def get_patient_history(self, patient_id: int, acting_user: User) -> list:
        patient = self.patients.get_by_id(patient_id)
        if patient is None:
            raise NotFoundError("Paciente não encontrado.")

        if acting_user.role == UserRole.PATIENT and patient.user_id != acting_user.id:
            raise ForbiddenError("Você não tem permissão para acessar este histórico.")
        if acting_user.role not in {
            UserRole.ADMIN,
            UserRole.DOCTOR,
            UserRole.NURSE,
            UserRole.RECEPTIONIST,
            UserRole.PATIENT,
        }:
            raise ForbiddenError("Você não tem permissão para acessar este histórico.")

        return self.repository.get_history_for_patient(patient_id)

    def _get_record(self, record_id: int) -> MedicalRecord:
        record = self.repository.get_by_id(record_id)
        if record is None:
            raise NotFoundError("Prontuário não encontrado.")
        return record

    def _authorize_responsible_doctor(self, appointment, acting_user: User) -> None:
        if acting_user.role != UserRole.DOCTOR:
            raise ForbiddenError("Apenas médicos podem registrar prontuário, prescrições e exames.")

        professional = self.professionals.get_by_user_id(acting_user.id)
        if professional is None or professional.id != appointment.doctor_id:
            raise ForbiddenError("Apenas o médico responsável pela consulta pode realizar esta ação.")

    def _authorize_view(self, record: MedicalRecord, acting_user: User) -> None:
        appointment = record.appointment
        if acting_user.role in {UserRole.ADMIN, UserRole.DOCTOR, UserRole.NURSE, UserRole.RECEPTIONIST}:
            return
        if acting_user.role == UserRole.PATIENT and appointment.patient.user_id == acting_user.id:
            return
        raise ForbiddenError("Você não tem permissão para acessar este prontuário.")
