from sqlalchemy.orm import Session
from app.models.medical_record import MedicalRecord
from .base_repository import BaseRepository


class MedicalRecordRepository(BaseRepository[MedicalRecord]):
    def __init__(self, db: Session):
        super().__init__(db, MedicalRecord)

    def get_by_appointment_id(self, appointment_id: int) -> MedicalRecord | None:
        return self.db.query(MedicalRecord).filter(
            MedicalRecord.appointment_id == appointment_id
        ).first()
