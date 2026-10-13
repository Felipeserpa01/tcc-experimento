from sqlalchemy.orm import Session
from app.models import Prescription

class PrescriptionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, prescription_id: int):
        return self.db.query(Prescription).filter(Prescription.id == prescription_id).first()

    def get_by_medical_record(self, medical_record_id: int):
        return self.db.query(Prescription).filter(
            Prescription.medical_record_id == medical_record_id
        ).all()

    def get_all(self, skip: int = 0, limit: int = 100):
        return self.db.query(Prescription).offset(skip).limit(limit).all()

    def create(self, prescription: Prescription):
        self.db.add(prescription)
        self.db.commit()
        self.db.refresh(prescription)
        return prescription

    def update(self, prescription: Prescription):
        self.db.commit()
        self.db.refresh(prescription)
        return prescription

    def delete(self, prescription_id: int):
        prescription = self.get_by_id(prescription_id)
        if prescription:
            self.db.delete(prescription)
            self.db.commit()
            return True
        return False
