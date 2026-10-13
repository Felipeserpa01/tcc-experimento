from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.clinical import ExamRequest
from app.models.enums import AppointmentStatus
from app.models.patient import HealthInsurance, Patient
from app.models.professional import Professional
from tests.factories import API, make_appointment, make_doctor, make_insurance, make_patient, token_for


@pytest.fixture
def completed(db: Session, patient: Patient, doctor: Professional) -> int:
    return make_appointment(db, patient, doctor, datetime(2030, 1, 7, 8, 0), status=AppointmentStatus.COMPLETED).id


def charge(client: TestClient, headers: dict, **payload):
    payload.setdefault("payment_method", "pix")
    return client.post(f"{API}/billing/charges", json=payload, headers=headers)


class TestCreateCharge:
    def test_uses_doctor_fee_without_insurance(self, client: TestClient, reception_h: dict, completed: int) -> None:
        response = charge(client, reception_h, appointment_id=completed)
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["gross_amount"] == "200.00"
        assert body["discount_amount"] == "0.00"
        assert body["net_amount"] == "200.00"
        assert body["status"] == "pendente"
        assert body["description"].startswith("Consulta - Cardiologia")

    def test_applies_insurance_discount(
        self, client: TestClient, reception_h: dict, db: Session, doctor: Professional, insurance: HealthInsurance
    ) -> None:
        insured = make_patient(db, full_name="Paciente Conveniado", insurance=insurance)
        appointment = make_appointment(db, insured, doctor, datetime(2030, 1, 7, 8, 0), AppointmentStatus.COMPLETED)
        response = charge(client, reception_h, appointment_id=appointment.id, payment_method="convenio")
        body = response.json()
        assert body["discount_percent"] == "20.00"
        assert body["discount_amount"] == "40.00"
        assert body["net_amount"] == "160.00"
        assert body["insurance_name"] == "Saúde Total"

    def test_fractional_discount_rounding(
        self, client: TestClient, reception_h: dict, db: Session, doctor: Professional
    ) -> None:
        plan = make_insurance(db, name="Plano Quebrado", discount="12.50")
        insured = make_patient(db, insurance=plan)
        appointment = make_appointment(db, insured, doctor, datetime(2030, 1, 7, 8, 0), AppointmentStatus.COMPLETED)
        body = charge(client, reception_h, appointment_id=appointment.id, amount="99.90").json()
        assert (body["discount_amount"], body["net_amount"]) == ("12.49", "87.41")

    def test_inactive_insurance_gives_no_discount(
        self, client: TestClient, reception_h: dict, db: Session, doctor: Professional
    ) -> None:
        plan = make_insurance(db, name="Plano Suspenso", discount="30", active=False)
        insured = make_patient(db, insurance=plan)
        appointment = make_appointment(db, insured, doctor, datetime(2030, 1, 7, 8, 0), AppointmentStatus.COMPLETED)
        body = charge(client, reception_h, appointment_id=appointment.id).json()
        assert body["net_amount"] == "200.00"
        response = charge(client, reception_h, appointment_id=appointment.id, payment_method="convenio")
        assert response.status_code == 409  # já existe cobrança ativa

    def test_insurance_payment_requires_insurance(self, client: TestClient, reception_h: dict, completed: int) -> None:
        response = charge(client, reception_h, appointment_id=completed, payment_method="convenio")
        assert response.status_code == 422

    def test_exactly_one_item(self, client: TestClient, reception_h: dict, completed: int) -> None:
        assert charge(client, reception_h).status_code == 422
        assert charge(client, reception_h, appointment_id=completed, exam_id=1).status_code == 422

    @pytest.mark.parametrize("amount", ["0", "-10", "10.555", "1000000.01", "abc"])
    def test_invalid_amounts(self, client: TestClient, reception_h: dict, completed: int, amount: str) -> None:
        assert charge(client, reception_h, appointment_id=completed, amount=amount).status_code == 422

    def test_duplicate_charge_is_blocked_until_cancelled(
        self, client: TestClient, reception_h: dict, completed: int
    ) -> None:
        first = charge(client, reception_h, appointment_id=completed).json()
        assert charge(client, reception_h, appointment_id=completed).status_code == 409
        client.post(
            f"{API}/billing/charges/{first['id']}/cancel", json={"reason": "Valor incorreto"}, headers=reception_h
        )
        assert charge(client, reception_h, appointment_id=completed, amount="180.00").status_code == 201

    def test_cancelled_or_missed_appointments_are_not_billable(
        self, client: TestClient, reception_h: dict, db: Session, patient: Patient, doctor: Professional
    ) -> None:
        for status in (AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW):
            appointment = make_appointment(db, patient, doctor, datetime(2030, 1, 3, 9, 0), status)
            assert charge(client, reception_h, appointment_id=appointment.id).status_code == 422

    def test_fee_required_when_doctor_has_none(
        self, client: TestClient, reception_h: dict, db: Session, patient: Patient
    ) -> None:
        volunteer = make_doctor(db, full_name="Sem Valor", fee=None)
        appointment = make_appointment(db, patient, volunteer, datetime(2030, 1, 3, 9, 0), AppointmentStatus.COMPLETED)
        assert charge(client, reception_h, appointment_id=appointment.id).status_code == 422
        assert charge(client, reception_h, appointment_id=appointment.id, amount="90").status_code == 201

    def test_exam_charge(
        self, client: TestClient, reception_h: dict, db: Session, completed: int, patient: Patient, doctor: Professional
    ) -> None:
        exam = ExamRequest(
            appointment_id=completed, patient_id=patient.id, professional_id=doctor.id, exam_name="Hemograma completo"
        )
        db.add(exam)
        db.commit()
        assert charge(client, reception_h, exam_id=exam.id).status_code == 422  # valor obrigatório
        response = charge(client, reception_h, exam_id=exam.id, amount="45.50", payment_method="dinheiro")
        assert response.status_code == 201
        assert response.json()["description"] == "Exame - Hemograma completo"
        assert charge(client, reception_h, exam_id=999, amount="10").status_code == 404

    def test_only_billing_staff_creates_charges(
        self, client: TestClient, doctor_h: dict, patient_h: dict, completed: int
    ) -> None:
        assert charge(client, doctor_h, appointment_id=completed).status_code == 403
        assert charge(client, patient_h, appointment_id=completed).status_code == 403


class TestPayment:
    @pytest.fixture
    def charge_id(self, client: TestClient, reception_h: dict, completed: int) -> int:
        return charge(client, reception_h, appointment_id=completed).json()["id"]

    def test_pay_and_prevent_double_payment(self, client: TestClient, reception_h: dict, charge_id: int) -> None:
        url = f"{API}/billing/charges/{charge_id}/pay"
        paid = client.post(url, json={"payment_method": "cartao_credito", "amount_paid": "200.00"}, headers=reception_h)
        assert paid.status_code == 200
        body = paid.json()
        assert body["status"] == "pago"
        assert body["payment_method"] == "cartao_credito"
        assert body["paid_amount"] == "200.00"
        assert body["paid_at"] == "2030-01-07T08:00:00"

        again = client.post(url, json={}, headers=reception_h)
        assert again.status_code == 409
        assert again.json()["error"]["code"] == "cobranca_ja_paga"

    def test_amount_must_match(self, client: TestClient, reception_h: dict, charge_id: int) -> None:
        response = client.post(
            f"{API}/billing/charges/{charge_id}/pay", json={"amount_paid": "150.00"}, headers=reception_h
        )
        assert response.status_code == 422
        assert response.json()["error"]["details"]["valor_cobranca"] == "200.00"

    def test_cancel_rules(self, client: TestClient, reception_h: dict, charge_id: int) -> None:
        cancel_url = f"{API}/billing/charges/{charge_id}/cancel"
        assert client.post(cancel_url, json={"reason": "x"}, headers=reception_h).status_code == 422
        cancelled = client.post(cancel_url, json={"reason": "Lançamento em duplicidade"}, headers=reception_h)
        assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelado"
        pay = client.post(f"{API}/billing/charges/{charge_id}/pay", json={}, headers=reception_h)
        assert pay.status_code == 409 and pay.json()["error"]["code"] == "cobranca_cancelada"
        assert client.post(cancel_url, json={"reason": "De novo, cancelar"}, headers=reception_h).status_code == 409

    def test_paid_charge_cannot_be_cancelled(self, client: TestClient, reception_h: dict, charge_id: int) -> None:
        client.post(f"{API}/billing/charges/{charge_id}/pay", json={}, headers=reception_h)
        response = client.post(
            f"{API}/billing/charges/{charge_id}/cancel", json={"reason": "Estorno solicitado"}, headers=reception_h
        )
        assert response.status_code == 409

    def test_patient_sees_only_own_charges(
        self, client: TestClient, db: Session, patient_h: dict, charge_id: int, reception_h: dict, doctor: Professional
    ) -> None:
        assert client.get(f"{API}/billing/charges/{charge_id}", headers=patient_h).status_code == 200
        assert client.post(f"{API}/billing/charges/{charge_id}/pay", json={}, headers=patient_h).status_code == 403

        stranger = make_patient(db, full_name="Outra Pessoa", with_user=True, email="outra@clinica.com.br")
        assert client.get(f"{API}/billing/charges/{charge_id}", headers=token_for(stranger.user)).status_code == 403
        assert client.get(f"{API}/billing/charges", headers=token_for(stranger.user)).json()["total"] == 0

    def test_list_filters(self, client: TestClient, reception_h: dict, charge_id: int) -> None:
        client.post(f"{API}/billing/charges/{charge_id}/pay", json={}, headers=reception_h)
        paid = client.get(f"{API}/billing/charges", params={"status": "pago"}, headers=reception_h).json()
        assert paid["total"] == 1
        pending = client.get(f"{API}/billing/charges", params={"status": "pendente"}, headers=reception_h).json()
        assert pending["total"] == 0
        by_method = client.get(
            f"{API}/billing/charges", params={"payment_method": "boleto"}, headers=reception_h
        ).json()
        assert by_method["total"] == 0
