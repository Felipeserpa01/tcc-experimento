from typing import Any, ClassVar

from sqlalchemy import func, select

from app.core.pagination import PageParams, PageResult, SortParams
from app.models.enums import ProfessionalType
from app.models.professional import Availability, Professional
from app.repositories.base import BaseRepository, contains_ci


class ProfessionalRepository(BaseRepository[Professional]):
    model = Professional
    sortable_columns: ClassVar[dict[str, Any]] = {
        "full_name": Professional.full_name,
        "specialty": Professional.specialty,
        "created_at": Professional.created_at,
    }

    def crm_exists(self, crm: str, exclude_id: int | None = None) -> bool:
        stmt = select(Professional.id).where(Professional.crm == crm)
        if exclude_id is not None:
            stmt = stmt.where(Professional.id != exclude_id)
        return self.db.scalar(stmt) is not None

    def coren_exists(self, coren: str, exclude_id: int | None = None) -> bool:
        stmt = select(Professional.id).where(Professional.coren == coren)
        if exclude_id is not None:
            stmt = stmt.where(Professional.id != exclude_id)
        return self.db.scalar(stmt) is not None

    def search(
        self,
        page: PageParams,
        sort: SortParams,
        *,
        name: str | None = None,
        specialty: str | None = None,
        professional_type: ProfessionalType | None = None,
        is_active: bool | None = True,
    ) -> PageResult[Professional]:
        stmt = select(Professional)
        if name:
            stmt = stmt.where(contains_ci(Professional.full_name, name))
        if specialty:
            stmt = stmt.where(contains_ci(Professional.specialty, specialty))
        if professional_type is not None:
            stmt = stmt.where(Professional.professional_type == professional_type)
        if is_active is not None:
            stmt = stmt.where(Professional.is_active == is_active)
        return self.paginate(stmt, page, sort)

    def list_specialties(self) -> list[str]:
        stmt = (
            select(Professional.specialty)
            .where(
                Professional.professional_type == ProfessionalType.DOCTOR,
                Professional.is_active.is_(True),
                Professional.specialty.is_not(None),
            )
            .group_by(func.lower(Professional.specialty))
            .order_by(func.lower(Professional.specialty))
        )
        return [row for row in self.db.scalars(stmt).all() if row]


class AvailabilityRepository(BaseRepository[Availability]):
    model = Availability

    def list_for_weekday(self, professional_id: int, weekday: int) -> list[Availability]:
        stmt = (
            select(Availability)
            .where(Availability.professional_id == professional_id, Availability.weekday == weekday)
            .order_by(Availability.start_time)
        )
        return list(self.db.scalars(stmt).all())
