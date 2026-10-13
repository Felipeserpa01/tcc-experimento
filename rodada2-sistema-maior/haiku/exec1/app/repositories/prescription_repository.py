from sqlalchemy.orm import Session
from app.models.prescription import Prescription
from .base_repository import BaseRepository


class PrescriptionRepository(BaseRepository[Prescription]):
    def __init__(self, db: Session):
        super().__init__(db, Prescription)

    def get_by_appointment_id(self, appointment_id: int):
        return self.db.query(Prescription).filter(
            Prescription.appointment_id == appointment_id
        ).all()
