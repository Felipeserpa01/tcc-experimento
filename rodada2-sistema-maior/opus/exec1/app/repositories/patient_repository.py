"""Repositorios de paciente e convenio."""

from __future__ import annotations

from sqlalchemy import func, or_, select

from app.core.pagination import PaginationParams
from app.models.patient import HealthInsurance, Patient
from app.repositories.base import BaseRepository
from app.utils.validators import strip_non_digits

PATIENT_SORT_FIELDS = {
    "id": Patient.id,
    "full_name": Patient.full_name,
    "cpf": Patient.cpf,
    "birth_date": Patient.birth_date,
    "created_at": Patient.created_at,
    "updated_at": Patient.updated_at,
}


class HealthInsuranceRepository(BaseRepository[HealthInsurance]):
    model = HealthInsurance

    def get_by_name(self, name: str) -> HealthInsurance | None:
        stmt = select(HealthInsurance).where(func.lower(HealthInsurance.name) == name.strip().lower())
        return self.db.execute(stmt).scalars().first()

    def search(
        self, pagination: PaginationParams, *, query: str | None = None, is_active: bool | None = None
    ) -> tuple[list[HealthInsurance], int]:
        stmt = select(HealthInsurance)
        if query:
            stmt = stmt.where(HealthInsurance.name.ilike(f"%{query.strip()}%"))
        if is_active is not None:
            stmt = stmt.where(HealthInsurance.is_active.is_(is_active))
        stmt = stmt.order_by(HealthInsurance.name.asc())
        return self.paginate(stmt, pagination.page, pagination.size)


class PatientRepository(BaseRepository[Patient]):
    model = Patient

    def get_by_cpf(self, cpf: str) -> Patient | None:
        return self.get_by(cpf=strip_non_digits(cpf))

    def get_by_user_id(self, user_id: int) -> Patient | None:
        return self.get_by(user_id=user_id)

    def cpf_taken(self, cpf: str, *, exclude_id: int | None = None) -> bool:
        stmt = select(func.count()).select_from(Patient).where(Patient.cpf == strip_non_digits(cpf))
        if exclude_id:
            stmt = stmt.where(Patient.id != exclude_id)
        return (self.db.execute(stmt).scalar_one() or 0) > 0

    def search(
        self,
        pagination: PaginationParams,
        *,
        query: str | None = None,
        cpf: str | None = None,
        insurance_id: int | None = None,
        insurance_name: str | None = None,
        city: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[Patient], int]:
        stmt = select(Patient)

        if query:
            term = query.strip()
            digits = strip_non_digits(term)
            conditions = [Patient.full_name.ilike(f"%{term}%")]
            if digits:
                conditions.append(Patient.cpf.like(f"{digits}%"))
            stmt = stmt.where(or_(*conditions))
        if cpf:
            digits = strip_non_digits(cpf)
            if digits:
                stmt = stmt.where(Patient.cpf.like(f"{digits}%"))
        if insurance_id is not None:
            stmt = stmt.where(Patient.insurance_id == insurance_id)
        if insurance_name:
            stmt = stmt.join(HealthInsurance, Patient.insurance_id == HealthInsurance.id).where(
                HealthInsurance.name.ilike(f"%{insurance_name.strip()}%")
            )
        if city:
            stmt = stmt.where(Patient.address_city.ilike(f"%{city.strip()}%"))
        if is_active is not None:
            stmt = stmt.where(Patient.is_active.is_(is_active))

        column, descending = pagination.resolve_sort(PATIENT_SORT_FIELDS, "full_name")
        stmt = self.apply_order(stmt, column, descending)
        return self.paginate(stmt, pagination.page, pagination.size)
