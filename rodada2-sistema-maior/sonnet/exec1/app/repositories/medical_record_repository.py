from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.medical_record import Exam, MedicalRecord, Prescription


class MedicalRecordRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, record_id: int) -> MedicalRecord | None:
        return self.db.get(MedicalRecord, record_id)

    def get_by_appointment_id(self, appointment_id: int) -> MedicalRecord | None:
        stmt = select(MedicalRecord).where(MedicalRecord.appointment_id == appointment_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, record: MedicalRecord) -> MedicalRecord:
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def add_prescription(self, prescription: Prescription) -> Prescription:
        self.db.add(prescription)
        self.db.commit()
        self.db.refresh(prescription)
        return prescription

    def add_exam(self, exam: Exam) -> Exam:
        self.db.add(exam)
        self.db.commit()
        self.db.refresh(exam)
        return exam

    def get_exam_by_id(self, exam_id: int) -> Exam | None:
        return self.db.get(Exam, exam_id)

    def update_exam(self, exam: Exam) -> Exam:
        self.db.commit()
        self.db.refresh(exam)
        return exam

    def get_history_for_patient(self, patient_id: int) -> list:
        from app.models.appointment import Appointment

        stmt = (
            select(Appointment)
            .where(Appointment.patient_id == patient_id)
            .order_by(Appointment.scheduled_at.desc())
        )
        return self.db.execute(stmt).scalars().all()
