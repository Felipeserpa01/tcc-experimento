from sqlalchemy.orm import Session
from datetime import datetime
from fastapi import HTTPException, status
from app.models import Charge, Patient, Appointment, Exam
from app.schemas import ChargeCreate, ChargeUpdate
from app.repositories.charge_repository import ChargeRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.exam_repository import ExamRepository

class BillingService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ChargeRepository(db)
        self.patient_repo = PatientRepository(db)
        self.appt_repo = AppointmentRepository(db)
        self.exam_repo = ExamRepository(db)

    def create_charge(self, charge_data: ChargeCreate) -> dict:
        patient = self.patient_repo.get_by_id(charge_data.patient_id)
        if not patient:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

        if charge_data.amount <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount must be positive")

        discount = 0.0
        if charge_data.appointment_id:
            appt = self.appt_repo.get_by_id(charge_data.appointment_id)
            if not appt:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

            if patient.insurance_plan:
                discount = charge_data.amount * 0.1

        if charge_data.exam_id:
            exam = self.exam_repo.get_by_id(charge_data.exam_id)
            if not exam:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

        charge = Charge(
            patient_id=charge_data.patient_id,
            appointment_id=charge_data.appointment_id,
            exam_id=charge_data.exam_id,
            amount=charge_data.amount,
            insurance_discount=discount,
            payment_method=charge_data.payment_method,
            status=charge_data.status
        )
        return self.repo.create(charge)

    def get_charge(self, charge_id: int):
        charge = self.repo.get_by_id(charge_id)
        if not charge:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Charge not found")
        return charge

    def pay_charge(self, charge_id: int, payment_method: str, charge_update: ChargeUpdate):
        charge = self.get_charge(charge_id)

        if charge.status == "pago":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Charge already paid")

        charge.status = "pago"
        charge.payment_method = payment_method
        charge.paid_at = datetime.utcnow()

        return self.repo.update(charge)

    def cancel_charge(self, charge_id: int):
        charge = self.get_charge(charge_id)

        if charge.status == "pago":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot cancel paid charge")

        charge.status = "cancelado"
        return self.repo.update(charge)

    def get_patient_charges(self, patient_id: int, skip: int = 0, limit: int = 100):
        self.patient_repo.get_by_id(patient_id)
        return self.repo.get_by_patient(patient_id, skip, limit)

    def get_unpaid_charges(self, patient_id: int):
        self.patient_repo.get_by_id(patient_id)
        return self.repo.get_unpaid_by_patient(patient_id)

    def get_charges_by_status(self, status: str, skip: int = 0, limit: int = 100):
        return self.repo.get_by_status(status, skip, limit)
