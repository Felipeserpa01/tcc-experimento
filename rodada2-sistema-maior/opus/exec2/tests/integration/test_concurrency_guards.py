"""Proteções contra condições de corrida (verificação de aplicação + garantia no banco)."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.models.billing import Charge
from app.models.enums import AppointmentStatus, ChargeStatus
from app.models.patient import Patient
from app.models.professional import Professional
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.schemas.billing import ChargePayment
from app.services.billing_service import BillingService
from tests.factories import API, make_appointment


def test_database_rejects_two_active_appointments_in_same_slot(
    db: Session, patient: Patient, other_patient: Patient, doctor: Professional
) -> None:
    make_appointment(db, patient, doctor, datetime(2030, 1, 8, 9, 0))
    with pytest.raises(IntegrityError):
        make_appointment(db, other_patient, doctor, datetime(2030, 1, 8, 9, 0))
    db.rollback()
    # Uma consulta cancelada não bloqueia o horário.
    make_appointment(db, other_patient, doctor, datetime(2030, 1, 8, 10, 0), status=AppointmentStatus.CANCELLED)
    make_appointment(db, patient, doctor, datetime(2030, 1, 8, 10, 0))


def test_race_on_booking_returns_conflict(
    client: TestClient,
    reception_h: dict,
    db: Session,
    patient: Patient,
    other_patient: Patient,
    doctor: Professional,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Simula duas requisições que passaram pela verificação ao mesmo tempo."""
    make_appointment(db, other_patient, doctor, datetime(2030, 1, 8, 9, 0))
    monkeypatch.setattr(AppointmentRepository, "find_overlapping", lambda *args, **kwargs: [])
    response = client.post(
        f"{API}/appointments",
        json={"patient_id": patient.id, "professional_id": doctor.id, "start_at": "2030-01-08T09:00:00"},
        headers=reception_h,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "horario_ocupado"


def test_database_rejects_second_active_charge(db: Session, patient: Patient, doctor: Professional) -> None:
    appointment = make_appointment(db, patient, doctor, datetime(2030, 1, 7, 8, 0), AppointmentStatus.COMPLETED)

    def new_charge() -> Charge:
        return Charge(
            patient_id=patient.id,
            appointment_id=appointment.id,
            description="Consulta",
            gross_amount=100,
            net_amount=100,
            payment_method="pix",
            status=ChargeStatus.PENDING,
        )

    db.add(new_charge())
    db.commit()
    db.add(new_charge())
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_concurrent_payment_is_detected(
    client: TestClient, db: Session, reception_h: dict, receptionist: User, patient: Patient, doctor: Professional
) -> None:
    appointment = make_appointment(db, patient, doctor, datetime(2030, 1, 7, 8, 0), AppointmentStatus.COMPLETED)
    charge_id = client.post(
        f"{API}/billing/charges", json={"appointment_id": appointment.id, "payment_method": "pix"}, headers=reception_h
    ).json()["id"]

    service = BillingService(db)
    stale = service.get(receptionist, charge_id)
    assert stale.status == ChargeStatus.PENDING
    # Outra requisição paga a cobrança "por baixo" enquanto esta ainda vê o status pendente.
    db.execute(
        update(Charge)
        .where(Charge.id == charge_id)
        .values(status=ChargeStatus.PAID)
        .execution_options(synchronize_session=False)
    )
    db.commit()  # a outra transação já foi confirmada; o objeto em memória continua "pendente"
    with pytest.raises(ConflictError) as exc:
        service.pay(receptionist, charge_id, ChargePayment())
    assert exc.value.code == "cobranca_ja_paga"
