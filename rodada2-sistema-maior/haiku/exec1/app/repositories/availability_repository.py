from sqlalchemy.orm import Session
from app.models.availability import AvailabilitySlot
from app.core.enums import Weekday
from .base_repository import BaseRepository


class AvailabilityRepository(BaseRepository[AvailabilitySlot]):
    def __init__(self, db: Session):
        super().__init__(db, AvailabilitySlot)

    def get_by_professional_and_weekday(self, professional_id: int, weekday: Weekday):
        return self.db.query(AvailabilitySlot).filter(
            AvailabilitySlot.professional_id == professional_id,
            AvailabilitySlot.weekday == weekday
        ).all()

    def get_professional_availability(self, professional_id: int):
        return self.db.query(AvailabilitySlot).filter(
            AvailabilitySlot.professional_id == professional_id
        ).order_by(AvailabilitySlot.weekday).all()
