"""Data access for Patient, with search/pagination/sorting."""
from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from app.models.patient import Patient

SORTABLE_FIELDS = {
    "nome": Patient.nome,
    "cpf": Patient.cpf,
    "created_at": Patient.created_at,
    "data_nascimento": Patient.data_nascimento,
}


class PatientRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, patient_id: int) -> Patient | None:
        return self.db.get(Patient, patient_id)

    def get_by_cpf(self, cpf: str) -> Patient | None:
        stmt = select(Patient).where(Patient.cpf == cpf)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_user_id(self, user_id: int) -> Patient | None:
        stmt = select(Patient).where(Patient.user_id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, patient: Patient) -> Patient:
        self.db.add(patient)
        self.db.flush()
        return patient

    def update(self, patient: Patient) -> Patient:
        self.db.add(patient)
        self.db.flush()
        return patient

    def delete(self, patient: Patient) -> None:
        self.db.delete(patient)
        self.db.flush()

    def search(
        self,
        nome: str | None,
        cpf: str | None,
        convenio: str | None,
        page: int,
        page_size: int,
        sort_by: str | None,
        sort_order: str,
    ) -> tuple[list[Patient], int]:
        stmt = select(Patient)
        if nome:
            stmt = stmt.where(Patient.nome.ilike(f"%{nome}%"))
        if cpf:
            stmt = stmt.where(Patient.cpf.ilike(f"%{cpf}%"))
        if convenio:
            stmt = stmt.where(Patient.convenio.ilike(f"%{convenio}%"))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()

        sort_column = SORTABLE_FIELDS.get(sort_by or "nome", Patient.nome)
        order_func = desc if sort_order == "desc" else asc
        stmt = stmt.order_by(order_func(sort_column))
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        items = list(self.db.execute(stmt).scalars().all())
        return items, total
