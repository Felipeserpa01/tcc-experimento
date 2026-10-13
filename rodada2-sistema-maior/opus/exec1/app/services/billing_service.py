"""Faturamento: geracao de cobranca, desconto de convenio e pagamento."""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.core.datetime_utils import now
from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.pagination import PaginationParams
from app.models.billing import Charge
from app.models.enums import (
    FRONT_DESK_ROLES,
    AppointmentStatus,
    AuditStatus,
    ChargeStatus,
    ChargeType,
    ExamStatus,
    PaymentMethod,
    UserRole,
)
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.billing_repository import ChargeRepository
from app.repositories.medical_record_repository import ExamRepository
from app.repositories.patient_repository import PatientRepository
from app.schemas.billing import ChargeCancelRequest, ChargeCreate, ChargePaymentRequest
from app.services.audit_service import AuditAction, AuditService

CENTS = Decimal("0.01")


def money(value: Decimal | float | int | None) -> Decimal:
    """Normaliza qualquer valor monetario para 2 casas decimais."""
    if value is None:
        return Decimal("0.00")
    return Decimal(str(value)).quantize(CENTS, rounding=ROUND_HALF_UP)


class BillingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = ChargeRepository(db)
        self.appointments = AppointmentRepository(db)
        self.exams = ExamRepository(db)
        self.patients = PatientRepository(db)
        self.audit = AuditService(db)

    # ==================================================================
    # Autorizacao
    # ==================================================================
    @staticmethod
    def ensure_can_manage(actor: User) -> None:
        if actor.role not in FRONT_DESK_ROLES:
            raise PermissionDeniedError(
                "Apenas administradores e recepcionistas gerenciam o faturamento."
            )

    def ensure_can_read(self, actor: User, charge: Charge) -> None:
        if actor.role in FRONT_DESK_ROLES:
            return
        if actor.role == UserRole.PATIENT:
            own = self.patients.get_by_user_id(actor.id)
            if own is not None and own.id == charge.patient_id:
                return
        raise PermissionDeniedError("Voce so pode acessar as proprias cobrancas.")

    # ==================================================================
    # Criacao
    # ==================================================================
    def create(self, payload: ChargeCreate, actor: User) -> Charge:
        self.ensure_can_manage(actor)

        patient_id = payload.patient_id
        appointment = None
        exam = None
        description = payload.description
        gross = payload.gross_amount

        if payload.charge_type == ChargeType.APPOINTMENT:
            appointment = self.appointments.get(payload.appointment_id)
            if appointment is None:
                raise NotFoundError(f"Consulta {payload.appointment_id} nao encontrada.")
            if appointment.status == AppointmentStatus.CANCELLED:
                raise BusinessRuleError("Nao e possivel cobrar por uma consulta cancelada.")
            if self.repository.has_open_charge_for_appointment(appointment.id):
                raise ConflictError(
                    "Ja existe uma cobranca ativa para esta consulta.",
                    details={"appointment_id": appointment.id},
                )
            patient_id = appointment.patient_id
            gross = gross if gross is not None else appointment.professional.appointment_price
            description = description or (
                f"Consulta com {appointment.professional.full_name} em "
                f"{appointment.scheduled_start:%d/%m/%Y %H:%M}"
            )

        elif payload.charge_type == ChargeType.EXAM:
            exam = self.exams.get(payload.exam_id)
            if exam is None:
                raise NotFoundError(f"Exame {payload.exam_id} nao encontrado.")
            if exam.status == ExamStatus.CANCELLED:
                raise BusinessRuleError("Nao e possivel cobrar por um exame cancelado.")
            if self.repository.has_open_charge_for_exam(exam.id):
                raise ConflictError(
                    "Ja existe uma cobranca ativa para este exame.",
                    details={"exam_id": exam.id},
                )
            patient_id = exam.patient_id
            gross = gross if gross is not None else exam.price
            description = description or f"Exame: {exam.exam_name}"

        patient = self.patients.get(patient_id)
        if patient is None:
            raise NotFoundError(f"Paciente {patient_id} nao encontrado.")

        gross_amount = money(gross)
        if gross_amount <= 0:
            raise BusinessRuleError(
                "Valor da cobranca deve ser maior que zero. "
                "Informe `gross_amount` ou cadastre o valor no profissional/exame."
            )

        discount_percent = Decimal("0.00")
        insurance_name = None
        if payload.apply_insurance_discount and patient.insurance and patient.insurance.is_active:
            discount_percent = money(patient.insurance.discount_percent)
            insurance_name = patient.insurance.name

        discount_amount = money(gross_amount * discount_percent / Decimal("100"))
        net_amount = money(gross_amount - discount_amount)
        if net_amount < 0:
            net_amount = Decimal("0.00")

        charge = Charge(
            patient_id=patient.id,
            appointment_id=appointment.id if appointment else None,
            exam_id=exam.id if exam else None,
            charge_type=payload.charge_type,
            description=description or "Servico avulso",
            gross_amount=gross_amount,
            discount_percent=discount_percent,
            discount_amount=discount_amount,
            net_amount=net_amount,
            status=ChargeStatus.PENDING,
            payment_method=payload.payment_method,
            insurance_name=insurance_name,
            due_date=payload.due_date,
            created_by_id=actor.id,
        )
        self.db.add(charge)
        self.db.flush()

        self.audit.record(
            action=AuditAction.CHARGE_CREATED,
            actor=actor,
            resource_type="charge",
            resource_id=charge.id,
            description=(
                f"Cobranca de R$ {net_amount} gerada para '{patient.full_name}' "
                f"({charge.charge_type.value})."
            ),
            extra={
                "gross_amount": str(gross_amount),
                "discount_percent": str(discount_percent),
                "net_amount": str(net_amount),
            },
        )
        self.db.commit()
        self.db.refresh(charge)
        return charge

    # ==================================================================
    # Leitura
    # ==================================================================
    def get(self, charge_id: int, actor: User) -> Charge:
        charge = self.repository.get(charge_id)
        if charge is None:
            raise NotFoundError(f"Cobranca {charge_id} nao encontrada.")
        self.ensure_can_read(actor, charge)
        return charge

    def search(
        self,
        pagination: PaginationParams,
        actor: User,
        *,
        patient_id: int | None = None,
        appointment_id: int | None = None,
        status: ChargeStatus | None = None,
        charge_type: ChargeType | None = None,
        payment_method: PaymentMethod | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[list[Charge], int]:
        if actor.role == UserRole.PATIENT:
            own = self.patients.get_by_user_id(actor.id)
            if own is None:
                return [], 0
            if patient_id is not None and patient_id != own.id:
                raise PermissionDeniedError("Voce so pode acessar as proprias cobrancas.")
            patient_id = own.id
        elif actor.role not in FRONT_DESK_ROLES:
            raise PermissionDeniedError("Perfil sem acesso ao faturamento.")

        return self.repository.search(
            pagination,
            patient_id=patient_id,
            appointment_id=appointment_id,
            status=status,
            charge_type=charge_type,
            payment_method=payment_method,
            start_date=start_date,
            end_date=end_date,
        )

    # ==================================================================
    # Pagamento
    # ==================================================================
    def register_payment(
        self, charge_id: int, payload: ChargePaymentRequest, actor: User
    ) -> Charge:
        self.ensure_can_manage(actor)
        charge = self.repository.get(charge_id)
        if charge is None:
            raise NotFoundError(f"Cobranca {charge_id} nao encontrada.")

        # Regra central: nao permitir pagar duas vezes.
        if charge.status == ChargeStatus.PAID:
            self.audit.record(
                action=AuditAction.CHARGE_PAID,
                actor=actor,
                resource_type="charge",
                resource_id=charge.id,
                description="Tentativa de pagar uma cobranca ja quitada.",
                status=AuditStatus.FAILURE,
            )
            self.db.commit()
            raise ConflictError(
                "Esta cobranca ja foi paga.",
                details={
                    "paid_at": charge.paid_at.isoformat() if charge.paid_at else None,
                    "paid_amount": str(charge.paid_amount),
                },
            )
        if charge.status == ChargeStatus.CANCELLED:
            raise ConflictError("Nao e possivel pagar uma cobranca cancelada.")

        amount = money(payload.amount) if payload.amount is not None else money(charge.net_amount)
        if amount != money(charge.net_amount):
            raise BusinessRuleError(
                "O valor informado difere do valor liquido da cobranca.",
                details={"expected": str(money(charge.net_amount)), "received": str(amount)},
            )

        charge.status = ChargeStatus.PAID
        charge.payment_method = payload.payment_method
        charge.paid_amount = amount
        charge.paid_at = now()
        charge.payment_reference = payload.payment_reference
        charge.paid_by_id = actor.id
        self.db.flush()

        self.audit.record(
            action=AuditAction.CHARGE_PAID,
            actor=actor,
            resource_type="charge",
            resource_id=charge.id,
            description=(
                f"Pagamento de R$ {amount} registrado "
                f"({payload.payment_method.value})."
            ),
        )
        self.db.commit()
        self.db.refresh(charge)
        return charge

    def cancel(self, charge_id: int, payload: ChargeCancelRequest, actor: User) -> Charge:
        self.ensure_can_manage(actor)
        charge = self.repository.get(charge_id)
        if charge is None:
            raise NotFoundError(f"Cobranca {charge_id} nao encontrada.")

        if charge.status == ChargeStatus.CANCELLED:
            raise ConflictError("Cobranca ja esta cancelada.")
        if charge.status == ChargeStatus.PAID:
            raise ConflictError(
                "Cobranca ja paga nao pode ser cancelada; registre um estorno."
            )

        charge.status = ChargeStatus.CANCELLED
        charge.cancelled_at = now()
        charge.cancellation_reason = payload.reason
        self.db.flush()

        self.audit.record(
            action=AuditAction.CHARGE_CANCELLED,
            actor=actor,
            resource_type="charge",
            resource_id=charge.id,
            description=f"Cobranca cancelada. Motivo: {payload.reason}",
        )
        self.db.commit()
        self.db.refresh(charge)
        return charge
