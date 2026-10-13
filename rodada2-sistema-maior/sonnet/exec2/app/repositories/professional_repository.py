"""Data access for Professional and AvailabilitySlot."""
from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session, joinedload

from app.core.enums import ProfessionalType
from app.models.professional import AvailabilitySlot, Professional

SORTABLE_FIELDS = {
    "nome": Professional.nome,
    "especialidade": Professional.especialidade,
    "created_at": Professional.created_at,
}


class ProfessionalRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, professional_id: int) -> Professional | None:
        stmt = (
            select(Professional)
            .options(joinedload(Professional.availability_slots))
            .where(Professional.id == professional_id)
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def get_by_crm(self, crm: str) -> Professional | None:
        stmt = select(Professional).where(Professional.crm == crm)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_user_id(self, user_id: int) -> Professional | None:
        stmt = select(Professional).where(Professional.user_id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, professional: Professional) -> Professional:
        self.db.add(professional)
        self.db.flush()
        return professional

    def update(self, professional: Professional) -> Professional:
        self.db.add(professional)
        self.db.flush()
        return professional

    def delete(self, professional: Professional) -> None:
        self.db.delete(professional)
        self.db.flush()

    def search(
        self,
        especialidade: str | None,
        tipo: ProfessionalType | None,
        page: int,
        page_size: int,
        sort_by: str | None,
        sort_order: str,
    ) -> tuple[list[Professional], int]:
        stmt = select(Professional).options(joinedload(Professional.availability_slots))
        if especialidade:
            stmt = stmt.where(Professional.especialidade.ilike(f"%{especialidade}%"))
        if tipo:
            stmt = stmt.where(Professional.tipo == tipo)

        count_stmt = select(func.count(Professional.id.distinct())).select_from(Professional)
        if especialidade:
            count_stmt = count_stmt.where(Professional.especialidade.ilike(f"%{especialidade}%"))
        if tipo:
            count_stmt = count_stmt.where(Professional.tipo == tipo)
        total = self.db.execute(count_stmt).scalar_one()

        sort_column = SORTABLE_FIELDS.get(sort_by or "nome", Professional.nome)
        order_func = desc if sort_order == "desc" else asc
        stmt = stmt.order_by(order_func(sort_column)).offset((page - 1) * page_size).limit(page_size)

        items = list(self.db.execute(stmt).unique().scalars().all())
        return items, total

    def add_availability_slot(self, slot: AvailabilitySlot) -> AvailabilitySlot:
        self.db.add(slot)
        self.db.flush()
        return slot

    def get_availability_slot(self, slot_id: int) -> AvailabilitySlot | None:
        return self.db.get(AvailabilitySlot, slot_id)

    def delete_availability_slot(self, slot: AvailabilitySlot) -> None:
        self.db.delete(slot)
        self.db.flush()
