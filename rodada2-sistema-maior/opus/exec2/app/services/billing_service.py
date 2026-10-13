"""Faturamento: cobranças de consultas e exames."""

from datetime import date
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import clock
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.pagination import PageParams, PageResult, SortParams
from app.models.billing import Charge
from app.models.enums import AppointmentStatus, ChargeStatus, ExamStatus, PaymentMethod
from app.models.patient import Patient
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.billing_repository import ChargeRepository
from app.repositories.clinical_repository import ExamRequestRepository
from app.schemas.billing import ChargeCreate, ChargePayment
from app.services import access
from app.services.audit_service import AuditAction, AuditService
from app.utils.money import apply_discount, to_money

_NON_BILLABLE_APPOINTMENT_STATUSES = frozenset({AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW})
_DUPLICATE_MESSAGE = "Já existe uma cobrança ativa (pendente ou paga) para este item."


class BillingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.charges = ChargeRepository(db)
        self.appointments = AppointmentRepository(db)
        self.exams = ExamRequestRepository(db)
        self.audit = AuditService(db)

    def get(self, actor: User, charge_id: int) -> Charge:
        charge = self.charges.get(charge_id)
        if charge is None:
            raise NotFoundError("Cobrança não encontrada.")
        access.ensure_patient_scope(actor, charge.patient_id)
        return charge

    def search(
        self,
        actor: User,
        page: PageParams,
        sort: SortParams,
        *,
        patient_id: int | None,
        status: ChargeStatus | None,
        payment_method: PaymentMethod | None,
        date_from: date | None,
        date_to: date | None,
    ) -> PageResult[Charge]:
        if date_from and date_to and date_from > date_to:
            raise BusinessRuleError("'date_from' deve ser anterior ou igual a 'date_to'.")
        if access.is_patient(actor):
            patient_id = access.own_patient_id(actor)
        return self.charges.search(
            page,
            sort,
            patient_id=patient_id,
            status=status,
            payment_method=payment_method,
            date_from=date_from,
            date_to=date_to,
        )

    # ------------------------------------------------------------------ criação
    def _resolve_item(self, data: ChargeCreate) -> tuple[Patient, Decimal, str]:
        """Retorna (paciente, valor bruto, descrição padrão) do item a ser cobrado."""
        if data.appointment_id is not None:
            appointment = self.appointments.get(data.appointment_id)
            if appointment is None:
                raise NotFoundError("Consulta não encontrada.")
            if appointment.status in _NON_BILLABLE_APPOINTMENT_STATUSES:
                raise BusinessRuleError(f"Não é possível cobrar uma consulta com status '{appointment.status.value}'.")
            if self.charges.find_active_for_appointment(appointment.id):
                raise ConflictError(_DUPLICATE_MESSAGE)
            amount = data.amount or appointment.professional.consultation_fee
            if amount is None:
                raise BusinessRuleError("Informe o valor: o médico não possui valor de consulta padrão cadastrado.")
            description = (
                f"Consulta - {appointment.professional.specialty or 'clínica geral'} - "
                f"{appointment.start_at.strftime('%d/%m/%Y %H:%M')}"
            )
            return appointment.patient, amount, description

        exam = self.exams.get(data.exam_id)  # type: ignore[arg-type]
        if exam is None:
            raise NotFoundError("Exame não encontrado.")
        if exam.status == ExamStatus.CANCELLED:
            raise BusinessRuleError("Não é possível cobrar um exame cancelado.")
        if self.charges.find_active_for_exam(exam.id):
            raise ConflictError(_DUPLICATE_MESSAGE)
        if data.amount is None:
            raise BusinessRuleError("Informe o valor ('amount') da cobrança do exame.")
        return exam.appointment.patient, data.amount, f"Exame - {exam.exam_name}"

    def create(self, actor: User, data: ChargeCreate) -> Charge:
        patient, gross, default_description = self._resolve_item(data)

        insurance = patient.insurance if patient.insurance and patient.insurance.is_active else None
        if data.payment_method == PaymentMethod.INSURANCE and insurance is None:
            raise BusinessRuleError("Pagamento via convênio exige que o paciente possua convênio ativo.")
        discount_percent = insurance.discount_percent if insurance else Decimal("0")
        breakdown = apply_discount(to_money(gross), discount_percent)

        charge = Charge(
            patient_id=patient.id,
            appointment_id=data.appointment_id,
            exam_id=data.exam_id,
            description=data.description or default_description,
            gross_amount=breakdown.gross,
            discount_percent=breakdown.percent,
            discount_amount=breakdown.discount,
            net_amount=breakdown.net,
            payment_method=data.payment_method,
            status=ChargeStatus.PENDING,
            insurance_id=insurance.id if insurance else None,
            created_by_id=actor.id,
        )
        self.db.add(charge)
        try:
            self.db.flush()
        except IntegrityError as exc:  # corrida entre duas requisições para o mesmo item
            self.db.rollback()
            raise ConflictError(_DUPLICATE_MESSAGE) from exc
        self.audit.log(
            AuditAction.CHARGE_CREATED,
            actor=actor,
            entity_type="cobranca",
            entity_id=charge.id,
            details={
                "valor_bruto": str(breakdown.gross),
                "desconto": str(breakdown.discount),
                "valor_liquido": str(breakdown.net),
            },
        )
        self.db.commit()
        self.db.refresh(charge)
        return charge

    # ------------------------------------------------------------------ pagamento / cancelamento
    def _raise_for_final_status(self, charge: Charge) -> None:
        if charge.status == ChargeStatus.PAID:
            raise ConflictError(
                "Esta cobrança já foi paga; não é possível registrar o pagamento novamente.",
                code="cobranca_ja_paga",
            )
        if charge.status == ChargeStatus.CANCELLED:
            raise ConflictError("Esta cobrança está cancelada.", code="cobranca_cancelada")

    def pay(self, actor: User, charge_id: int, data: ChargePayment) -> Charge:
        charge = self.get(actor, charge_id)
        self._raise_for_final_status(charge)
        if data.amount_paid is not None and to_money(data.amount_paid) != charge.net_amount:
            raise BusinessRuleError(
                "O valor pago difere do valor da cobrança. Pagamentos parciais não são aceitos.",
                details={"valor_cobranca": str(charge.net_amount), "valor_informado": str(data.amount_paid)},
            )
        method = data.payment_method or charge.payment_method
        if method == PaymentMethod.INSURANCE and charge.insurance_id is None:
            raise BusinessRuleError("Pagamento via convênio exige cobrança vinculada a um convênio.")

        now = clock.now()
        updated = self.charges.transition_from_pending(
            charge.id,
            ChargeStatus.PAID,
            paid_at=now,
            paid_amount=charge.net_amount,
            payment_method=method,
            paid_registered_by_id=actor.id,
            updated_at=now,
        )
        if not updated:  # outra requisição alterou o status entre a leitura e a escrita
            self.db.rollback()
            self.db.refresh(charge)
            self._raise_for_final_status(charge)
            raise ConflictError("Não foi possível registrar o pagamento. Tente novamente.")

        self.audit.log(
            AuditAction.CHARGE_PAID,
            actor=actor,
            entity_type="cobranca",
            entity_id=charge.id,
            details={"valor": str(charge.net_amount), "forma_pagamento": method.value},
        )
        self.db.commit()
        self.db.refresh(charge)
        return charge

    def cancel(self, actor: User, charge_id: int, reason: str) -> Charge:
        charge = self.get(actor, charge_id)
        if charge.status == ChargeStatus.PAID:
            raise ConflictError("Cobranças pagas não podem ser canceladas.", code="cobranca_ja_paga")
        if charge.status == ChargeStatus.CANCELLED:
            raise ConflictError("Esta cobrança já está cancelada.", code="cobranca_cancelada")
        now = clock.now()
        if not self.charges.transition_from_pending(
            charge.id, ChargeStatus.CANCELLED, cancelled_at=now, cancellation_reason=reason, updated_at=now
        ):
            self.db.rollback()
            raise ConflictError("A cobrança foi alterada por outra operação. Recarregue e tente novamente.")
        self.audit.log(
            AuditAction.CHARGE_CANCELLED,
            actor=actor,
            entity_type="cobranca",
            entity_id=charge.id,
            details={"motivo": reason},
        )
        self.db.commit()
        self.db.refresh(charge)
        return charge
