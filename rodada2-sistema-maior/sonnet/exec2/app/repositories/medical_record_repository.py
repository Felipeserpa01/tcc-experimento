"""Data access for MedicalRecord, Prescription and Exam."""
from sqlalchemy import asc, select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.medical_record import Exam, MedicalRecord, Prescription
from app.models.patient import Patient


class MedicalRecordRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_appointment_id(self, appointment_id: int) -> MedicalRecord | None:
        stmt = select(MedicalRecord).where(MedicalRecord.appointment_id == appointment_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, record: MedicalRecord) -> MedicalRecord:
        self.db.add(record)
        self.db.flush()
        return record

    def create_prescription(self, prescription: Prescription) -> Prescription:
        self.db.add(prescription)
        self.db.flush()
        return prescription

    def get_prescriptions_by_appointment(self, appointment_id: int) -> list[Prescription]:
        stmt = select(Prescription).where(Prescription.appointment_id == appointment_id)
        return list(self.db.execute(stmt).scalars().all())

    def create_exam(self, exam: Exam) -> Exam:
        self.db.add(exam)
        self.db.flush()
        return exam

    def get_exam_by_id(self, exam_id: int) -> Exam | None:
        return self.db.get(Exam, exam_id)

    def update_exam(self, exam: Exam) -> Exam:
        self.db.add(exam)
        self.db.flush()
        return exam

    def get_exams_by_appointment(self, appointment_id: int) -> list[Exam]:
        stmt = select(Exam).where(Exam.appointment_id == appointment_id)
        return list(self.db.execute(stmt).scalars().all())

    def get_patient_history(self, patient_id: int) -> list[Appointment]:
        """Returns all appointments for a patient (with related data), ordered chronologically."""
        stmt = (
            select(Appointment)
            .where(Appointment.patient_id == patient_id)
            .order_by(asc(Appointment.data_hora))
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_patient_by_id(self, patient_id: int) -> Patient | None:
        return self.db.get(Patient, patient_id)
