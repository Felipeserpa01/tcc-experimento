from sqlalchemy import select

from app.models.clinical import ExamRequest, MedicalRecord, Prescription
from app.repositories.base import BaseRepository


class MedicalRecordRepository(BaseRepository[MedicalRecord]):
    model = MedicalRecord

    def get_by_appointment(self, appointment_id: int) -> MedicalRecord | None:
        return self.db.scalar(select(MedicalRecord).where(MedicalRecord.appointment_id == appointment_id))


class PrescriptionRepository(BaseRepository[Prescription]):
    model = Prescription

    def list_by_appointment(self, appointment_id: int) -> list[Prescription]:
        stmt = select(Prescription).where(Prescription.appointment_id == appointment_id).order_by(Prescription.id)
        return list(self.db.scalars(stmt).all())


class ExamRequestRepository(BaseRepository[ExamRequest]):
    model = ExamRequest

    def list_by_appointment(self, appointment_id: int) -> list[ExamRequest]:
        stmt = select(ExamRequest).where(ExamRequest.appointment_id == appointment_id).order_by(ExamRequest.id)
        return list(self.db.scalars(stmt).all())
