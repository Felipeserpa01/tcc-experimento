from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models import Professional, User, AvailabilitySchedule
from app.schemas import ProfessionalCreate, AvailabilityScheduleCreate
from app.repositories.professional_repository import ProfessionalRepository
from app.repositories.availability_schedule_repository import AvailabilityScheduleRepository
from app.utils import validate_crm

class ProfessionalService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ProfessionalRepository(db)
        self.schedule_repo = AvailabilityScheduleRepository(db)

    def create_professional(self, prof_data: ProfessionalCreate) -> dict:
        if not validate_crm(prof_data.registration_number):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid CRM")

        existing = self.repo.get_by_registration_number(prof_data.registration_number)
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CRM already registered")

        user = self.db.query(User).filter(User.id == prof_data.user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        professional = Professional(**prof_data.dict())
        return self.repo.create(professional)

    def get_professional(self, professional_id: int):
        professional = self.repo.get_by_id(professional_id)
        if not professional:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professional not found")
        return professional

    def list_professionals(self, skip: int = 0, limit: int = 100, specialization: str = None):
        return self.repo.search(skip, limit, specialization)

    def add_availability_schedule(self, schedule_data: AvailabilityScheduleCreate):
        professional = self.get_professional(schedule_data.professional_id)

        if not 0 <= schedule_data.day_of_week <= 6:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid day of week")

        if schedule_data.start_time >= schedule_data.end_time:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Start time must be before end time")

        schedule = AvailabilitySchedule(**schedule_data.dict())
        return self.schedule_repo.create(schedule)

    def get_availability_schedules(self, professional_id: int):
        self.get_professional(professional_id)
        return self.schedule_repo.get_by_professional(professional_id)

    def delete_schedule(self, schedule_id: int):
        return self.schedule_repo.delete(schedule_id)

    def delete_professional(self, professional_id: int):
        return self.repo.delete(professional_id)
