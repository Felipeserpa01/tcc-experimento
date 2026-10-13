from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.patient import Patient


class PatientRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, patient_id: int) -> Patient | None:
        return self.db.get(Patient, patient_id)

    def get_by_user_id(self, user_id: int) -> Patient | None:
        stmt = select(Patient).where(Patient.user_id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_cpf(self, cpf: str) -> Patient | None:
        stmt = select(Patient).where(Patient.cpf == cpf)
        return self.db.execute(stmt).scalar_one_or_none()

    def search(
        self,
        name: str | None,
        cpf: str | None,
        insurance: str | None,
        order_by: str,
        descending: bool,
        offset: int,
        limit: int,
    ) -> tuple[list[Patient], int]:
        stmt = select(Patient)
        if name:
            stmt = stmt.where(Patient.full_name.ilike(f"%{name}%"))
        if cpf:
            stmt = stmt.where(Patient.cpf == cpf)
        if insurance:
            stmt = stmt.where(Patient.insurance.ilike(f"%{insurance}%"))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()

        sort_column = getattr(Patient, order_by, Patient.full_name)
        stmt = stmt.order_by(sort_column.desc() if descending else sort_column.asc())
        stmt = stmt.offset(offset).limit(limit)
        items = self.db.execute(stmt).scalars().all()
        return items, total

    def create(self, patient: Patient) -> Patient:
        self.db.add(patient)
        self.db.commit()
        self.db.refresh(patient)
        return patient

    def update(self, patient: Patient) -> Patient:
        self.db.commit()
        self.db.refresh(patient)
        return patient

    def delete(self, patient: Patient) -> None:
        self.db.delete(patient)
        self.db.commit()
