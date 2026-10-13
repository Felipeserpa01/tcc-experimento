from sqlalchemy.orm import Session
from app.models.exam import Exam
from .base_repository import BaseRepository


class ExamRepository(BaseRepository[Exam]):
    def __init__(self, db: Session):
        super().__init__(db, Exam)

    def get_by_appointment_id(self, appointment_id: int):
        return self.db.query(Exam).filter(
            Exam.appointment_id == appointment_id
        ).all()
