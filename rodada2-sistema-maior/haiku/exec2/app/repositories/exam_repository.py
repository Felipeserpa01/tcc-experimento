from sqlalchemy.orm import Session
from app.models import Exam

class ExamRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, exam_id: int):
        return self.db.query(Exam).filter(Exam.id == exam_id).first()

    def get_by_medical_record(self, medical_record_id: int):
        return self.db.query(Exam).filter(
            Exam.medical_record_id == medical_record_id
        ).all()

    def get_by_status(self, status: str, skip: int = 0, limit: int = 100):
        return self.db.query(Exam).filter(
            Exam.status == status
        ).offset(skip).limit(limit).all()

    def get_all(self, skip: int = 0, limit: int = 100):
        return self.db.query(Exam).offset(skip).limit(limit).all()

    def create(self, exam: Exam):
        self.db.add(exam)
        self.db.commit()
        self.db.refresh(exam)
        return exam

    def update(self, exam: Exam):
        self.db.commit()
        self.db.refresh(exam)
        return exam

    def delete(self, exam_id: int):
        exam = self.get_by_id(exam_id)
        if exam:
            self.db.delete(exam)
            self.db.commit()
            return True
        return False
