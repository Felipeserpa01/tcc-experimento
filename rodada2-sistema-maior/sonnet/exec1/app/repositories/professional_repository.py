from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.professional import Availability, Professional


class ProfessionalRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, professional_id: int) -> Professional | None:
        return self.db.get(Professional, professional_id)

    def get_by_user_id(self, user_id: int) -> Professional | None:
        stmt = select(Professional).where(Professional.user_id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_license_number(self, license_number: str) -> Professional | None:
        stmt = select(Professional).where(Professional.license_number == license_number)
        return self.db.execute(stmt).scalar_one_or_none()

    def search(
        self, specialty: str | None, professional_type: str | None, offset: int, limit: int
    ) -> tuple[list[Professional], int]:
        stmt = select(Professional)
        if specialty:
            stmt = stmt.where(Professional.specialty.ilike(f"%{specialty}%"))
        if professional_type:
            stmt = stmt.where(Professional.professional_type == professional_type)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()

        stmt = stmt.order_by(Professional.full_name.asc()).offset(offset).limit(limit)
        items = self.db.execute(stmt).scalars().all()
        return items, total

    def create(self, professional: Professional) -> Professional:
        self.db.add(professional)
        self.db.commit()
        self.db.refresh(professional)
        return professional

    def update(self, professional: Professional) -> Professional:
        self.db.commit()
        self.db.refresh(professional)
        return professional

    def delete(self, professional: Professional) -> None:
        self.db.delete(professional)
        self.db.commit()

    def add_availability(self, availability: Availability) -> Availability:
        self.db.add(availability)
        self.db.commit()
        self.db.refresh(availability)
        return availability

    def get_availabilities(self, professional_id: int) -> list[Availability]:
        stmt = select(Availability).where(Availability.professional_id == professional_id)
        return self.db.execute(stmt).scalars().all()

    def get_availability_by_id(self, availability_id: int) -> Availability | None:
        return self.db.get(Availability, availability_id)
