from typing import Any, ClassVar

from sqlalchemy import func, or_, select

from app.core.pagination import PageParams, PageResult, SortParams
from app.models.patient import HealthInsurance, Patient
from app.repositories.base import BaseRepository, contains_ci, starts_with
from app.utils.validators import only_digits


class PatientRepository(BaseRepository[Patient]):
    model = Patient
    sortable_columns: ClassVar[dict[str, Any]] = {
        "full_name": Patient.full_name,
        "birth_date": Patient.birth_date,
        "created_at": Patient.created_at,
        "cpf": Patient.cpf,
    }

    def cpf_exists(self, cpf: str, exclude_id: int | None = None) -> bool:
        stmt = select(Patient.id).where(Patient.cpf == cpf)
        if exclude_id is not None:
            stmt = stmt.where(Patient.id != exclude_id)
        return self.db.scalar(stmt) is not None

    def search(
        self,
        page: PageParams,
        sort: SortParams,
        *,
        query: str | None = None,
        name: str | None = None,
        cpf: str | None = None,
        insurance_id: int | None = None,
        insurance_name: str | None = None,
        is_active: bool | None = True,
    ) -> PageResult[Patient]:
        stmt = select(Patient)
        if is_active is not None:
            stmt = stmt.where(Patient.is_active == is_active)
        if query:
            digits = only_digits(query)
            conditions = [contains_ci(Patient.full_name, query)]
            if digits:
                conditions.append(starts_with(Patient.cpf, digits))
            stmt = stmt.where(or_(*conditions))
        if name:
            stmt = stmt.where(contains_ci(Patient.full_name, name))
        if cpf:
            stmt = stmt.where(starts_with(Patient.cpf, only_digits(cpf)))
        if insurance_id is not None:
            stmt = stmt.where(Patient.insurance_id == insurance_id)
        if insurance_name:
            stmt = stmt.join(HealthInsurance, Patient.insurance_id == HealthInsurance.id).where(
                contains_ci(HealthInsurance.name, insurance_name)
            )
        return self.paginate(stmt, page, sort)


class InsuranceRepository(BaseRepository[HealthInsurance]):
    model = HealthInsurance
    sortable_columns: ClassVar[dict[str, Any]] = {
        "name": HealthInsurance.name,
        "discount_percent": HealthInsurance.discount_percent,
        "created_at": HealthInsurance.created_at,
    }

    def name_exists(self, name: str, exclude_id: int | None = None) -> bool:
        stmt = select(HealthInsurance.id).where(func.lower(HealthInsurance.name) == name.lower())
        if exclude_id is not None:
            stmt = stmt.where(HealthInsurance.id != exclude_id)
        return self.db.scalar(stmt) is not None

    def ans_code_exists(self, ans_code: str, exclude_id: int | None = None) -> bool:
        stmt = select(HealthInsurance.id).where(HealthInsurance.ans_code == ans_code)
        if exclude_id is not None:
            stmt = stmt.where(HealthInsurance.id != exclude_id)
        return self.db.scalar(stmt) is not None

    def search(
        self, page: PageParams, sort: SortParams, *, name: str | None = None, is_active: bool | None = None
    ) -> PageResult[HealthInsurance]:
        stmt = select(HealthInsurance)
        if name:
            stmt = stmt.where(contains_ci(HealthInsurance.name, name))
        if is_active is not None:
            stmt = stmt.where(HealthInsurance.is_active == is_active)
        return self.paginate(stmt, page, sort)
