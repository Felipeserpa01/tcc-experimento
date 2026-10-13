"""Repositorios de profissional e agenda."""

from __future__ import annotations

from datetime import time

from sqlalchemy import func, or_, select

from app.core.pagination import PaginationParams
from app.models.enums import CouncilType, ProfessionalType
from app.models.professional import Professional, ProfessionalSchedule
from app.repositories.base import BaseRepository

PROFESSIONAL_SORT_FIELDS = {
    "id": Professional.id,
    "full_name": Professional.full_name,
    "specialty": Professional.specialty,
    "created_at": Professional.created_at,
    "appointment_price": Professional.appointment_price,
}


class ProfessionalRepository(BaseRepository[Professional]):
    model = Professional

    def get_by_user_id(self, user_id: int) -> Professional | None:
        return self.get_by(user_id=user_id)

    def council_taken(
        self,
        council_type: CouncilType,
        council_number: str,
        council_state: str,
        *,
        exclude_id: int | None = None,
    ) -> bool:
        stmt = (
            select(func.count())
            .select_from(Professional)
            .where(
                Professional.council_type == council_type,
                Professional.council_number == council_number,
                Professional.council_state == council_state,
            )
        )
        if exclude_id:
            stmt = stmt.where(Professional.id != exclude_id)
        return (self.db.execute(stmt).scalar_one() or 0) > 0

    def search(
        self,
        pagination: PaginationParams,
        *,
        query: str | None = None,
        specialty: str | None = None,
        professional_type: ProfessionalType | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[Professional], int]:
        stmt = select(Professional)
        if query:
            term = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    Professional.full_name.ilike(term),
                    Professional.council_number.like(f"{query.strip()}%"),
                )
            )
        if specialty:
            stmt = stmt.where(Professional.specialty.ilike(f"%{specialty.strip()}%"))
        if professional_type:
            stmt = stmt.where(Professional.professional_type == professional_type)
        if is_active is not None:
            stmt = stmt.where(Professional.is_active.is_(is_active))

        column, descending = pagination.resolve_sort(PROFESSIONAL_SORT_FIELDS, "full_name")
        stmt = self.apply_order(stmt, column, descending)
        return self.paginate(stmt, pagination.page, pagination.size)

    def list_specialties(self) -> list[str]:
        stmt = (
            select(Professional.specialty)
            .where(Professional.specialty.is_not(None))
            .distinct()
            .order_by(Professional.specialty.asc())
        )
        return [row for row in self.db.execute(stmt).scalars().all() if row]


class ScheduleRepository(BaseRepository[ProfessionalSchedule]):
    model = ProfessionalSchedule

    def list_for_professional(
        self, professional_id: int, *, weekday: int | None = None, only_active: bool = False
    ) -> list[ProfessionalSchedule]:
        stmt = select(ProfessionalSchedule).where(
            ProfessionalSchedule.professional_id == professional_id
        )
        if weekday is not None:
            stmt = stmt.where(ProfessionalSchedule.weekday == weekday)
        if only_active:
            stmt = stmt.where(ProfessionalSchedule.is_active.is_(True))
        stmt = stmt.order_by(ProfessionalSchedule.weekday, ProfessionalSchedule.start_time)
        return list(self.db.execute(stmt).scalars().all())

    def find_overlapping(
        self,
        professional_id: int,
        weekday: int,
        start_time: time,
        end_time: time,
        *,
        exclude_id: int | None = None,
    ) -> ProfessionalSchedule | None:
        stmt = select(ProfessionalSchedule).where(
            ProfessionalSchedule.professional_id == professional_id,
            ProfessionalSchedule.weekday == weekday,
            ProfessionalSchedule.start_time < end_time,
            ProfessionalSchedule.end_time > start_time,
        )
        if exclude_id:
            stmt = stmt.where(ProfessionalSchedule.id != exclude_id)
        return self.db.execute(stmt.limit(1)).scalars().first()
