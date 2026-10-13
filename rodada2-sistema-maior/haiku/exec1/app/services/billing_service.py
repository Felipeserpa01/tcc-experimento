from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import NotFoundError, ConflictError, ValidationError, ForbiddenError
from app.core.enums import PaymentStatus, AuditAction
from app.models.billing import Charge, Payment
from app.models.user import User
from app.repositories.billing_repository import ChargeRepository, PaymentRepository
from app.repositories.patient_repository import PatientRepository
from app.services.audit_service import AuditService


class BillingService:
    def __init__(self, db: Session):
        self.db = db
        self.charge_repo = ChargeRepository(db)
        self.payment_repo = PaymentRepository(db)
        self.patient_repo = PatientRepository(db)
        self.audit_service = AuditService(db)

    def create_charge(
        self,
        patient_id: int,
        amount: float,
        appointment_id: int = None,
        exam_id: int = None,
        current_user: User = None
    ) -> Charge:
        # Verify patient exists
        patient = self.patient_repo.get(patient_id)
        if not patient:
            raise NotFoundError("Patient not found")

        # Ensure either appointment or exam is provided
        if not appointment_id and not exam_id:
            raise ValidationError("Either appointment_id or exam_id must be provided")

        # Calculate discount
        discount_amount = 0.0
        insurance_applied = False

        if patient.insurance_plan:
            discount_amount = amount * (settings.insurance_default_discount_percent / 100)
            insurance_applied = True

        final_amount = amount - discount_amount

        charge = self.charge_repo.create({
            "patient_id": patient_id,
            "appointment_id": appointment_id,
            "exam_id": exam_id,
            "amount": amount,
            "discount_amount": discount_amount,
            "final_amount": final_amount,
            "insurance_applied": insurance_applied,
            "status": PaymentStatus.PENDING
        })

        if current_user:
            self.audit_service.log(
                action=AuditAction.CHARGE_CREATED,
                user_id=current_user.id,
                entity_type="Charge",
                entity_id=charge.id
            )

        return charge

    def get_charge(self, charge_id: int, current_user: User = None) -> Charge:
        charge = self.charge_repo.get(charge_id)
        if not charge:
            raise NotFoundError("Charge not found")

        # Ownership check for patients
        if current_user and current_user.role.value == "patient":
            if charge.patient.user_id != current_user.id:
                raise ForbiddenError("Cannot access another patient's charges")

        return charge

    def register_payment(
        self,
        charge_id: int,
        amount_paid: float,
        payment_method: str,
        current_user: User
    ) -> Payment:
        charge = self.get_charge(charge_id, current_user)

        # Prevent payment if already paid or cancelled
        if charge.status == PaymentStatus.PAID:
            raise ConflictError("Charge has already been paid")

        if charge.status == PaymentStatus.CANCELLED:
            raise ConflictError("Cannot pay a cancelled charge")

        # Verify payment amount
        if amount_paid < charge.final_amount:
            raise ValidationError(f"Insufficient payment. Required: {charge.final_amount}, Provided: {amount_paid}")

        # Create payment record
        payment = self.payment_repo.create({
            "charge_id": charge_id,
            "amount_paid": amount_paid,
            "payment_method": payment_method
        })

        # Update charge status
        charge.status = PaymentStatus.PAID
        self.db.add(charge)
        self.db.commit()

        self.audit_service.log(
            action=AuditAction.PAYMENT_REGISTERED,
            user_id=current_user.id,
            entity_type="Payment",
            entity_id=payment.id,
            details={"charge_id": charge_id, "amount": amount_paid}
        )

        return payment

    def cancel_charge(self, charge_id: int, current_user: User) -> Charge:
        charge = self.get_charge(charge_id, current_user)

        if charge.status == PaymentStatus.CANCELLED:
            raise ValidationError("Charge is already cancelled")

        if charge.status == PaymentStatus.PAID:
            raise ConflictError("Cannot cancel a paid charge")

        charge.status = PaymentStatus.CANCELLED
        self.db.add(charge)
        self.db.commit()

        self.audit_service.log(
            action=AuditAction.CHARGE_CANCELLED,
            user_id=current_user.id,
            entity_type="Charge",
            entity_id=charge_id
        )

        return charge
