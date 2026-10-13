from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.billing import Charge, Payment
from app.core.enums import PaymentStatus
from .base_repository import BaseRepository


class ChargeRepository(BaseRepository[Charge]):
    def __init__(self, db: Session):
        super().__init__(db, Charge)

    def get_patient_charges(self, patient_id: int):
        return self.db.query(Charge).filter(
            Charge.patient_id == patient_id
        ).order_by(Charge.created_at.desc()).all()

    def get_by_appointment_id(self, appointment_id: int):
        return self.db.query(Charge).filter(
            Charge.appointment_id == appointment_id
        ).first()


class PaymentRepository(BaseRepository[Payment]):
    def __init__(self, db: Session):
        super().__init__(db, Payment)

    def get_by_charge_id(self, charge_id: int):
        return self.db.query(Payment).filter(
            Payment.charge_id == charge_id
        ).all()
