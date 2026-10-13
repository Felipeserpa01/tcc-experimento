from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models import Patient, User
from app.schemas import PatientCreate, PatientUpdate
from app.repositories.patient_repository import PatientRepository
from app.utils import validate_cpf

class PatientService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PatientRepository(db)

    def create_patient(self, patient_data: PatientCreate) -> dict:
        if not validate_cpf(patient_data.cpf):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid CPF")

        existing = self.repo.get_by_cpf(patient_data.cpf)
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CPF already registered")

        user = self.db.query(User).filter(User.id == patient_data.user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        patient = Patient(**patient_data.dict())
        return self.repo.create(patient)

    def get_patient(self, patient_id: int, current_user_id: int, current_user_role: str):
        patient = self.repo.get_by_id(patient_id)
        if not patient:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

        if current_user_role == "patient" and patient.user_id != current_user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        return patient

    def update_patient(self, patient_id: int, patient_data: PatientUpdate, current_user_id: int, current_user_role: str):
        patient = self.get_patient(patient_id, current_user_id, current_user_role)

        for field, value in patient_data.dict(exclude_unset=True).items():
            setattr(patient, field, value)

        return self.repo.update(patient)

    def list_patients(self, skip: int = 0, limit: int = 100, name: str = None, cpf: str = None,
                     insurance_plan: str = None, sort_by: str = "created_at"):
        return self.repo.search(skip, limit, name, cpf, insurance_plan, sort_by)

    def get_patient_by_cpf(self, cpf: str):
        return self.repo.get_by_cpf(cpf)

    def delete_patient(self, patient_id: int):
        return self.repo.delete(patient_id)
