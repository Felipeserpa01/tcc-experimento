from sqlalchemy.orm import Session
from app.models.professional import Professional
from app.core.enums import ProfessionalType
from .base_repository import BaseRepository


class ProfessionalRepository(BaseRepository[Professional]):
    def __init__(self, db: Session):
        super().__init__(db, Professional)

    def get_by_user_id(self, user_id: int) -> Professional | None:
        return self.db.query(Professional).filter(Professional.user_id == user_id).first()

    def get_by_license_number(self, license_number: str) -> Professional | None:
        return self.db.query(Professional).filter(Professional.license_number == license_number).first()

    def get_doctors_by_specialty(self, specialty: str):
        return self.db.query(Professional).filter(
            Professional.professional_type == ProfessionalType.DOCTOR,
            Professional.specialty == specialty
        ).all()

    def get_all_doctors(self):
        return self.db.query(Professional).filter(
            Professional.professional_type == ProfessionalType.DOCTOR
        ).all()
