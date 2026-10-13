from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models import Charge

class ChargeRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, charge_id: int):
        return self.db.query(Charge).filter(Charge.id == charge_id).first()

    def get_by_patient(self, patient_id: int, skip: int = 0, limit: int = 100):
        return self.db.query(Charge).filter(
            Charge.patient_id == patient_id
        ).order_by(Charge.created_at.desc()).offset(skip).limit(limit).all()

    def get_by_appointment(self, appointment_id: int):
        return self.db.query(Charge).filter(
            Charge.appointment_id == appointment_id
        ).all()

    def get_by_exam(self, exam_id: int):
        return self.db.query(Charge).filter(
            Charge.exam_id == exam_id
        ).all()

    def get_by_status(self, status: str, skip: int = 0, limit: int = 100):
        return self.db.query(Charge).filter(
            Charge.status == status
        ).offset(skip).limit(limit).all()

    def get_unpaid_by_patient(self, patient_id: int):
        return self.db.query(Charge).filter(
            and_(
                Charge.patient_id == patient_id,
                Charge.status == "pendente"
            )
        ).all()

    def get_all(self, skip: int = 0, limit: int = 100):
        return self.db.query(Charge).offset(skip).limit(limit).all()

    def create(self, charge: Charge):
        self.db.add(charge)
        self.db.commit()
        self.db.refresh(charge)
        return charge

    def update(self, charge: Charge):
        self.db.commit()
        self.db.refresh(charge)
        return charge

    def delete(self, charge_id: int):
        charge = self.get_by_id(charge_id)
        if charge:
            self.db.delete(charge)
            self.db.commit()
            return True
        return False
