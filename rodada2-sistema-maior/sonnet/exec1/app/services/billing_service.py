from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.billing import Billing
from app.models.enums import BillingStatus, PaymentMethod, UserRole
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.billing_repository import BillingRepository
from app.repositories.patient_repository import PatientRepository
from app.schemas.billing import BillingCreate
from app.services.audit_service import AuditService

INSURANCE_DISCOUNT_RATE = Decimal("0.30")


class BillingService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = BillingRepository(db)
        self.appointments = AppointmentRepository(db)
        self.patients = PatientRepository(db)
        self.audit = AuditService(db)

    def create_billing(
        self, payload: BillingCreate, acting_user: User, ip_address: str | None = None
    ) -> Billing:
        appointment = self.appointments.get_by_id(payload.appointment_id)
        if appointment is None:
            raise NotFoundError("Consulta não encontrada.")

        patient = self.patients.get_by_id(appointment.patient_id)

        discount = payload.discount
        if patient and patient.insurance and discount == 0:
            discount = (payload.amount * INSURANCE_DISCOUNT_RATE).quantize(Decimal("0.01"))

        final_amount = payload.amount - discount
        if final_amount < 0:
            final_amount = Decimal("0")

        billing = Billing(
            appointment_id=payload.appointment_id,
            amount=payload.amount,
            discount=discount,
            final_amount=final_amount,
            payment_method=payload.payment_method,
        )
        created = self.repository.create(billing)
        self.audit.log(acting_user.id, "CREATE_BILLING", "Billing", created.id, ip_address=ip_address)
        return created

    def get_billing(self, billing_id: int, acting_user: User) -> Billing:
        billing = self.repository.get_by_id(billing_id)
        if billing is None:
            raise NotFoundError("Cobrança não encontrada.")
        self._authorize_view(billing, acting_user)
        return billing

    def search(
        self,
        status: BillingStatus | None,
        payment_method: PaymentMethod | None,
        start: date | None,
        end: date | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Billing], int]:
        return self.repository.search(status, payment_method, start, end, offset, limit)

    def pay(
        self,
        billing_id: int,
        acting_user: User,
        payment_method: PaymentMethod | None = None,
        ip_address: str | None = None,
    ) -> Billing:
        billing = self.repository.get_by_id(billing_id)
        if billing is None:
            raise NotFoundError("Cobrança não encontrada.")

        if billing.status == BillingStatus.PAID:
            raise ConflictError("Esta cobrança já foi paga.")
        if billing.status == BillingStatus.CANCELLED:
            raise ConflictError("Não é possível pagar uma cobrança cancelada.")

        if payment_method:
            billing.payment_method = payment_method
        billing.status = BillingStatus.PAID
        billing.paid_at = datetime.now(timezone.utc)
        updated = self.repository.update(billing)
        self.audit.log(acting_user.id, "PAY_BILLING", "Billing", billing_id, ip_address=ip_address)
        return updated

    def cancel(self, billing_id: int, acting_user: User, ip_address: str | None = None) -> Billing:
        billing = self.repository.get_by_id(billing_id)
        if billing is None:
            raise NotFoundError("Cobrança não encontrada.")
        if billing.status == BillingStatus.PAID:
            raise ConflictError("Não é possível cancelar uma cobrança já paga.")

        billing.status = BillingStatus.CANCELLED
        updated = self.repository.update(billing)
        self.audit.log(acting_user.id, "CANCEL_BILLING", "Billing", billing_id, ip_address=ip_address)
        return updated

    def _authorize_view(self, billing: Billing, acting_user: User) -> None:
        if acting_user.role in {UserRole.ADMIN, UserRole.RECEPTIONIST}:
            return
        if acting_user.role == UserRole.PATIENT:
            patient = self.patients.get_by_user_id(acting_user.id)
            if patient and billing.appointment.patient_id == patient.id:
                return
        raise ForbiddenError("Você não tem permissão para acessar esta cobrança.")
