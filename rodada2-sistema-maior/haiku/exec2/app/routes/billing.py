from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models import UserRole
from app.schemas import ChargeCreate, ChargeUpdate, ChargeResponse
from app.services.billing_service import BillingService

router = APIRouter()

@router.post("/charges", response_model=ChargeResponse)
def create_charge(
    charge_data: ChargeCreate,
    current_user = Depends(require_role(UserRole.RECEPTIONIST, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    service = BillingService(db)
    return service.create_charge(charge_data)

@router.get("/charges/{charge_id}", response_model=ChargeResponse)
def get_charge(
    charge_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = BillingService(db)
    return service.get_charge(charge_id)

@router.post("/charges/{charge_id}/pay", response_model=ChargeResponse)
def pay_charge(
    charge_id: int,
    payment_method: str = Query(...),
    current_user = Depends(require_role(UserRole.RECEPTIONIST, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    service = BillingService(db)
    charge_update = ChargeUpdate(status="pago", payment_method=payment_method)
    return service.pay_charge(charge_id, payment_method, charge_update)

@router.post("/charges/{charge_id}/cancel", response_model=ChargeResponse)
def cancel_charge(
    charge_id: int,
    current_user = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    service = BillingService(db)
    return service.cancel_charge(charge_id)

@router.get("/patient/{patient_id}/charges", response_model=list)
def get_patient_charges(
    patient_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = BillingService(db)
    return service.get_patient_charges(patient_id, skip, limit)

@router.get("/patient/{patient_id}/charges/unpaid", response_model=list)
def get_unpaid_charges(
    patient_id: int,
    current_user = Depends(require_role(UserRole.PATIENT, UserRole.RECEPTIONIST)),
    db: Session = Depends(get_db)
):
    service = BillingService(db)
    return service.get_unpaid_charges(patient_id)

@router.get("/charges/status/{status}", response_model=list)
def get_charges_by_status(
    status: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user = Depends(require_role(UserRole.ADMIN, UserRole.RECEPTIONIST)),
    db: Session = Depends(get_db)
):
    service = BillingService(db)
    return service.get_charges_by_status(status, skip, limit)
