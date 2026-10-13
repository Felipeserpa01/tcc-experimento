"""Billing business logic: charges, insurance discounts, payment status."""
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.enums import BillableType, BillingStatus, UserRole
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app.models.billing import Billing
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.billing_repository import BillingRepository
from app.repositories.medical_record_repository import MedicalRecordRepository
from app.repositories.patient_repository import PatientRepository
from app.schemas.billing import BillingCreate, BillingPayment
from app.services.audit_service import AuditService

settings = get_settings()


class BillingService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = BillingRepository(db)
        self.appointment_repo = AppointmentRepository(db)
        self.medical_record_repo = MedicalRecordRepository(db)
        self.patient_repo = PatientRepository(db)
        self.audit = AuditService(db)

    def _ensure_staff(self, actor: User) -> None:
        if actor.role == UserRole.PACIENTE:
            raise ForbiddenError("Pacientes não podem gerenciar cobranças.")

    def create(self, data: BillingCreate, actor: User, ip_address: str | None = None) -> Billing:
        self._ensure_staff(actor)

        patient = self.patient_repo.get_by_id(data.patient_id)
        if not patient:
            raise NotFoundError("Paciente não encontrado.")

        if data.tipo == BillableType.CONSULTA:
            appointment = self.appointment_repo.get_by_id(data.appointment_id)
            if not appointment:
                raise NotFoundError("Consulta não encontrada.")
            if appointment.patient_id != data.patient_id:
                raise ValidationAppError("A consulta informada não pertence ao paciente informado.")
            if self.repo.get_by_appointment_id(data.appointment_id):
                raise ConflictError("Já existe uma cobrança ativa para esta consulta.")
        else:
            exam = self.medical_record_repo.get_exam_by_id(data.exam_id)
            if not exam:
                raise NotFoundError("Exame não encontrado.")
            if self.repo.get_by_exam_id(data.exam_id):
                raise ConflictError("Já existe uma cobrança ativa para este exame.")

        valor = Decimal(data.valor)
        desconto = Decimal("0.00")
        convenio_aplicado = False
        if data.aplicar_desconto_convenio:
            if not patient.convenio:
                raise ValidationAppError("Paciente não possui convênio cadastrado para aplicar desconto.")
            percent = Decimal(str(settings.convenio_discount_percent)) / Decimal("100")
            desconto = (valor * percent).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            convenio_aplicado = True

        valor_final = valor - desconto

        billing = Billing(
            patient_id=data.patient_id,
            appointment_id=data.appointment_id,
            exam_id=data.exam_id,
            tipo=data.tipo,
            valor=valor,
            valor_desconto=desconto,
            valor_final=valor_final,
            convenio_aplicado=convenio_aplicado,
            forma_pagamento=data.forma_pagamento,
            status=BillingStatus.PENDENTE,
            created_by=actor.id,
        )
        self.repo.create(billing)
        self.db.commit()
        self.audit.log(actor.id, "BILLING_CREATE", "Billing", billing.id, ip_address=ip_address)
        self.db.commit()
        return billing

    def get(self, billing_id: int, actor: User) -> Billing:
        billing = self.repo.get_by_id(billing_id)
        if not billing:
            raise NotFoundError("Cobrança não encontrada.")
        if actor.role == UserRole.PACIENTE and billing.patient.user_id != actor.id:
            raise ForbiddenError("Você só pode visualizar as suas próprias cobranças.")
        return billing

    def pay(self, billing_id: int, data: BillingPayment, actor: User, ip_address: str | None = None) -> Billing:
        self._ensure_staff(actor)
        billing = self.repo.get_by_id(billing_id)
        if not billing:
            raise NotFoundError("Cobrança não encontrada.")

        if billing.status == BillingStatus.PAGO:
            raise ConflictError("Esta cobrança já foi paga.")
        if billing.status == BillingStatus.CANCELADO:
            raise ConflictError("Não é possível pagar uma cobrança cancelada.")

        if data.forma_pagamento:
            billing.forma_pagamento = data.forma_pagamento
        billing.status = BillingStatus.PAGO
        billing.paid_at = datetime.now(timezone.utc)
        self.repo.update(billing)
        self.db.commit()
        self.audit.log(actor.id, "BILLING_PAID", "Billing", billing.id, ip_address=ip_address)
        self.db.commit()
        return billing

    def cancel(self, billing_id: int, actor: User, ip_address: str | None = None) -> Billing:
        self._ensure_staff(actor)
        billing = self.repo.get_by_id(billing_id)
        if not billing:
            raise NotFoundError("Cobrança não encontrada.")

        if billing.status == BillingStatus.PAGO:
            raise ConflictError("Não é possível cancelar uma cobrança já paga.")
        if billing.status == BillingStatus.CANCELADO:
            raise ConflictError("Esta cobrança já está cancelada.")

        billing.status = BillingStatus.CANCELADO
        self.repo.update(billing)
        self.db.commit()
        self.audit.log(actor.id, "BILLING_CANCEL", "Billing", billing.id, ip_address=ip_address)
        self.db.commit()
        return billing

    def search(
        self,
        actor: User,
        patient_id: int | None,
        status: BillingStatus | None,
        page: int,
        page_size: int,
        sort_by: str | None,
        sort_order: str,
    ) -> tuple[list[Billing], int]:
        if actor.role == UserRole.PACIENTE:
            own_patient = self.patient_repo.get_by_user_id(actor.id)
            if not own_patient:
                raise NotFoundError("Cadastro de paciente não encontrado para este usuário.")
            patient_id = own_patient.id

        return self.repo.search(patient_id, status, page, page_size, sort_by, sort_order)
