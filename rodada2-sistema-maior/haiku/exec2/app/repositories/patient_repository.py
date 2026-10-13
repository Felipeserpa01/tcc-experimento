from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models import Patient

class PatientRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, patient_id: int):
        return self.db.query(Patient).filter(Patient.id == patient_id).first()

    def get_by_user_id(self, user_id: int):
        return self.db.query(Patient).filter(Patient.user_id == user_id).first()

    def get_by_cpf(self, cpf: str):
        return self.db.query(Patient).filter(Patient.cpf == cpf).first()

    def search(self, skip: int = 0, limit: int = 100, name: str = None, cpf: str = None, insurance_plan: str = None, sort_by: str = "created_at"):
        query = self.db.query(Patient)

        if name:
            query = query.filter(Patient.user.has(full_name__ilike=f"%{name}%"))
        if cpf:
            query = query.filter(Patient.cpf.contains(cpf))
        if insurance_plan:
            query = query.filter(Patient.insurance_plan.ilike(f"%{insurance_plan}%"))

        if sort_by == "name":
            query = query.join(Patient.user).order_by("users.full_name")
        else:
            query = query.order_by(getattr(Patient, sort_by))

        return query.offset(skip).limit(limit).all()

    def get_all(self, skip: int = 0, limit: int = 100):
        return self.db.query(Patient).offset(skip).limit(limit).all()

    def create(self, patient: Patient):
        self.db.add(patient)
        self.db.commit()
        self.db.refresh(patient)
        return patient

    def update(self, patient: Patient):
        self.db.commit()
        self.db.refresh(patient)
        return patient

    def delete(self, patient_id: int):
        patient = self.get_by_id(patient_id)
        if patient:
            self.db.delete(patient)
            self.db.commit()
            return True
        return False
