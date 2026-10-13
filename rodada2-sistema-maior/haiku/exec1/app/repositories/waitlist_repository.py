from sqlalchemy.orm import Session
from app.models.waitlist import WaitlistEntry
from app.core.enums import WaitlistStatus
from .base_repository import BaseRepository


class WaitlistRepository(BaseRepository[WaitlistEntry]):
    def __init__(self, db: Session):
        super().__init__(db, WaitlistEntry)

    def get_waiting_for_doctor(self, doctor_id: int):
        return self.db.query(WaitlistEntry).filter(
            WaitlistEntry.doctor_id == doctor_id,
            WaitlistEntry.status == WaitlistStatus.WAITING
        ).order_by(WaitlistEntry.created_at).all()
