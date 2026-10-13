from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models import UserRole
from app.schemas import ProfessionalCreate, ProfessionalResponse, AvailabilityScheduleCreate, AvailabilityScheduleResponse
from app.services.professional_service import ProfessionalService

router = APIRouter()

@router.post("/", response_model=ProfessionalResponse)
def create_professional(
    prof_data: ProfessionalCreate,
    current_user = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    service = ProfessionalService(db)
    return service.create_professional(prof_data)

@router.get("/{professional_id}", response_model=ProfessionalResponse)
def get_professional(
    professional_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ProfessionalService(db)
    return service.get_professional(professional_id)

@router.get("/", response_model=list)
def list_professionals(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    specialization: str = Query(None),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ProfessionalService(db)
    return service.list_professionals(skip, limit, specialization)

@router.post("/{professional_id}/availability", response_model=AvailabilityScheduleResponse)
def add_availability(
    professional_id: int,
    schedule_data: AvailabilityScheduleCreate,
    current_user = Depends(require_role(UserRole.ADMIN, UserRole.DOCTOR)),
    db: Session = Depends(get_db)
):
    if schedule_data.professional_id != professional_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Professional ID mismatch")

    service = ProfessionalService(db)
    return service.add_availability_schedule(schedule_data)

@router.get("/{professional_id}/availability", response_model=list)
def get_availability(
    professional_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ProfessionalService(db)
    return service.get_availability_schedules(professional_id)

@router.delete("/availability/{schedule_id}", response_model=dict)
def delete_availability(
    schedule_id: int,
    current_user = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    service = ProfessionalService(db)
    if service.delete_schedule(schedule_id):
        return {"message": "Schedule deleted"}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")

@router.delete("/{professional_id}", response_model=dict)
def delete_professional(
    professional_id: int,
    current_user = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    service = ProfessionalService(db)
    if service.delete_professional(professional_id):
        return {"message": "Professional deleted"}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professional not found")
