from sqlalchemy.orm import Session
from app.models import Professional

class ProfessionalRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, professional_id: int):
        return self.db.query(Professional).filter(Professional.id == professional_id).first()

    def get_by_user_id(self, user_id: int):
        return self.db.query(Professional).filter(Professional.user_id == user_id).first()

    def get_by_registration_number(self, registration_number: str):
        return self.db.query(Professional).filter(Professional.registration_number == registration_number).first()

    def get_by_specialization(self, specialization: str, skip: int = 0, limit: int = 100):
        return self.db.query(Professional).filter(
            Professional.specialization.ilike(f"%{specialization}%")
        ).offset(skip).limit(limit).all()

    def get_all(self, skip: int = 0, limit: int = 100):
        return self.db.query(Professional).offset(skip).limit(limit).all()

    def search(self, skip: int = 0, limit: int = 100, specialization: str = None):
        query = self.db.query(Professional)
        if specialization:
            query = query.filter(Professional.specialization.ilike(f"%{specialization}%"))
        return query.offset(skip).limit(limit).all()

    def create(self, professional: Professional):
        self.db.add(professional)
        self.db.commit()
        self.db.refresh(professional)
        return professional

    def update(self, professional: Professional):
        self.db.commit()
        self.db.refresh(professional)
        return professional

    def delete(self, professional_id: int):
        professional = self.get_by_id(professional_id)
        if professional:
            self.db.delete(professional)
            self.db.commit()
            return True
        return False
