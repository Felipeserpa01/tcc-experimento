from sqlalchemy.orm import Session
from app.models import AvailabilitySchedule

class AvailabilityScheduleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, schedule_id: int):
        return self.db.query(AvailabilitySchedule).filter(AvailabilitySchedule.id == schedule_id).first()

    def get_by_professional(self, professional_id: int):
        return self.db.query(AvailabilitySchedule).filter(
            AvailabilitySchedule.professional_id == professional_id
        ).order_by(AvailabilitySchedule.day_of_week).all()

    def get_by_professional_and_day(self, professional_id: int, day_of_week: int):
        return self.db.query(AvailabilitySchedule).filter(
            AvailabilitySchedule.professional_id == professional_id,
            AvailabilitySchedule.day_of_week == day_of_week
        ).all()

    def get_all(self, skip: int = 0, limit: int = 100):
        return self.db.query(AvailabilitySchedule).offset(skip).limit(limit).all()

    def create(self, schedule: AvailabilitySchedule):
        self.db.add(schedule)
        self.db.commit()
        self.db.refresh(schedule)
        return schedule

    def update(self, schedule: AvailabilitySchedule):
        self.db.commit()
        self.db.refresh(schedule)
        return schedule

    def delete(self, schedule_id: int):
        schedule = self.get_by_id(schedule_id)
        if schedule:
            self.db.delete(schedule)
            self.db.commit()
            return True
        return False
