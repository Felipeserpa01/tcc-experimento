from sqlalchemy.orm import Session
from app.models import MedicalRecord

class MedicalRecordRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, record_id: int):
        return self.db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()

    def get_by_appointment(self, appointment_id: int):
        return self.db.query(MedicalRecord).filter(
            MedicalRecord.appointment_id == appointment_id
        ).first()

    def get_by_patient(self, patient_id: int, skip: int = 0, limit: int = 100):
        return self.db.query(MedicalRecord).filter(
            MedicalRecord.patient_id == patient_id
        ).order_by(MedicalRecord.created_at.desc()).offset(skip).limit(limit).all()

    def get_by_doctor(self, doctor_id: int, skip: int = 0, limit: int = 100):
        return self.db.query(MedicalRecord).filter(
            MedicalRecord.doctor_id == doctor_id
        ).order_by(MedicalRecord.created_at.desc()).offset(skip).limit(limit).all()

    def get_all(self, skip: int = 0, limit: int = 100):
        return self.db.query(MedicalRecord).offset(skip).limit(limit).all()

    def create(self, record: MedicalRecord):
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def update(self, record: MedicalRecord):
        self.db.commit()
        self.db.refresh(record)
        return record

    def delete(self, record_id: int):
        record = self.get_by_id(record_id)
        if record:
            self.db.delete(record)
            self.db.commit()
            return True
        return False
