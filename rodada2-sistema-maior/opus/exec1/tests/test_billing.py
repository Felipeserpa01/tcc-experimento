"""Testes de faturamento: desconto de convenio, pagamento e cancelamento."""

from __future__ import annotations


import pytest

from tests.conftest import API, auth_headers, next_weekday_at


@pytest.fixture()
def reception_headers(client, scenario):
    return auth_headers(client, "recepcao@clinica.com")


@pytest.fixture()
def doctor_headers(client, scenario):
    return auth_headers(client, "medico@clinica.com")


@pytest.fixture()
def patient_headers(client, scenario):
    return auth_headers(client, "paciente@clinica.com")


def book(client, headers, scenario, patient_key="patient", hour=9):
    return client.post(
        f"{API}/appointments",
        json={
            "patient_id": scenario[patient_key].id,
            "professional_id": scenario["doctor"].id,
            "scheduled_start": next_weekday_at(hour).isoformat(),
        },
        headers=headers,
    ).json()


class TestCreateCharge:
    def test_applies_insurance_discount(self, client, scenario, reception_headers):
        appointment = book(client, reception_headers, scenario)
        response = client.post(
            f"{API}/charges",
            json={"charge_type": "appointment", "appointment_id": appointment["id"]},
            headers=reception_headers,
        )
        assert response.status_code == 201, response.text
        body = response.json()
        # Preco 300.00 com 20% de desconto do convenio "Saude Total".
        assert body["gross_amount"] == "300.00"
        assert body["discount_percent"] == "20.00"
        assert body["discount_amount"] == "60.00"
        assert body["net_amount"] == "240.00"
        assert body["insurance_name"] == "Saude Total"
        assert body["status"] == "pending"

    def test_patient_without_insurance_pays_full_price(
        self, client, scenario, reception_headers
    ):
        appointment = book(client, reception_headers, scenario, patient_key="other_patient")
        response = client.post(
            f"{API}/charges",
            json={"charge_type": "appointment", "appointment_id": appointment["id"]},
            headers=reception_headers,
        )
        body = response.json()
        assert body["discount_amount"] == "0.00"
        assert body["net_amount"] == "300.00"
        assert body["insurance_name"] is None

    def test_can_skip_insurance_discount(self, client, scenario, reception_headers):
        appointment = book(client, reception_headers, scenario)
        response = client.post(
            f"{API}/charges",
            json={
                "charge_type": "appointment",
                "appointment_id": appointment["id"],
                "apply_insurance_discount": False,
            },
            headers=reception_headers,
        )
        assert response.json()["net_amount"] == "300.00"

    def test_custom_amount_overrides_price(self, client, scenario, reception_headers):
        appointment = book(client, reception_headers, scenario)
        response = client.post(
            f"{API}/charges",
            json={
                "charge_type": "appointment",
                "appointment_id": appointment["id"],
                "gross_amount": "500.00",
            },
            headers=reception_headers,
        )
        assert response.json()["gross_amount"] == "500.00"
        assert response.json()["net_amount"] == "400.00"

    def test_rejects_duplicate_charge_for_appointment(
        self, client, scenario, reception_headers
    ):
        appointment = book(client, reception_headers, scenario)
        payload = {"charge_type": "appointment", "appointment_id": appointment["id"]}
        client.post(f"{API}/charges", json=payload, headers=reception_headers)
        response = client.post(f"{API}/charges", json=payload, headers=reception_headers)
        assert response.status_code == 409

    def test_allows_new_charge_after_cancellation(self, client, scenario, reception_headers):
        appointment = book(client, reception_headers, scenario)
        payload = {"charge_type": "appointment", "appointment_id": appointment["id"]}
        charge = client.post(f"{API}/charges", json=payload, headers=reception_headers).json()
        client.post(
            f"{API}/charges/{charge['id']}/cancel",
            json={"reason": "Erro de lancamento"},
            headers=reception_headers,
        )
        response = client.post(f"{API}/charges", json=payload, headers=reception_headers)
        assert response.status_code == 201

    def test_rejects_charge_for_cancelled_appointment(
        self, client, scenario, reception_headers
    ):
        appointment = book(client, reception_headers, scenario)
        client.post(
            f"{API}/appointments/{appointment['id']}/cancel",
            json={"reason": "Desistencia"},
            headers=reception_headers,
        )
        response = client.post(
            f"{API}/charges",
            json={"charge_type": "appointment", "appointment_id": appointment["id"]},
            headers=reception_headers,
        )
        assert response.status_code == 422

    def test_exam_charge_uses_exam_price(
        self, client, scenario, reception_headers, doctor_headers
    ):
        appointment = book(client, reception_headers, scenario)
        client.post(f"{API}/appointments/{appointment['id']}/start", headers=doctor_headers)
        exam = client.post(
            f"{API}/appointments/{appointment['id']}/exams",
            json={"exam_name": "Ressonancia", "price": "900.00"},
            headers=doctor_headers,
        ).json()
        response = client.post(
            f"{API}/charges",
            json={"charge_type": "exam", "exam_id": exam["id"]},
            headers=reception_headers,
        )
        assert response.status_code == 201
        assert response.json()["gross_amount"] == "900.00"
        assert response.json()["net_amount"] == "720.00"

    def test_other_charge_requires_amount_and_description(
        self, client, scenario, reception_headers
    ):
        response = client.post(
            f"{API}/charges",
            json={"charge_type": "other", "patient_id": scenario["patient"].id},
            headers=reception_headers,
        )
        assert response.status_code == 422

    def test_other_charge_is_accepted(self, client, scenario, reception_headers):
        response = client.post(
            f"{API}/charges",
            json={
                "charge_type": "other",
                "patient_id": scenario["patient"].id,
                "description": "Curativo",
                "gross_amount": "80.00",
            },
            headers=reception_headers,
        )
        assert response.status_code == 201
        assert response.json()["net_amount"] == "64.00"

    def test_rejects_zero_amount(self, client, db, scenario, reception_headers):
        appointment = book(client, reception_headers, scenario)
        response = client.post(
            f"{API}/charges",
            json={
                "charge_type": "appointment",
                "appointment_id": appointment["id"],
                "gross_amount": "0",
            },
            headers=reception_headers,
        )
        assert response.status_code == 422

    def test_doctor_cannot_create_charge(self, client, scenario, reception_headers, doctor_headers):
        appointment = book(client, reception_headers, scenario)
        response = client.post(
            f"{API}/charges",
            json={"charge_type": "appointment", "appointment_id": appointment["id"]},
            headers=doctor_headers,
        )
        assert response.status_code == 403

    def test_patient_cannot_create_charge(self, client, scenario, reception_headers, patient_headers):
        appointment = book(client, reception_headers, scenario)
        response = client.post(
            f"{API}/charges",
            json={"charge_type": "appointment", "appointment_id": appointment["id"]},
            headers=patient_headers,
        )
        assert response.status_code == 403


class TestPayment:
    @pytest.fixture()
    def charge(self, client, scenario, reception_headers):
        appointment = book(client, reception_headers, scenario)
        return client.post(
            f"{API}/charges",
            json={"charge_type": "appointment", "appointment_id": appointment["id"]},
            headers=reception_headers,
        ).json()

    def test_registers_payment(self, client, charge, reception_headers):
        response = client.post(
            f"{API}/charges/{charge['id']}/pay",
            json={"payment_method": "pix"},
            headers=reception_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "paid"
        assert body["paid_amount"] == "240.00"
        assert body["payment_method"] == "pix"
        assert body["paid_at"] is not None

    def test_cannot_pay_twice(self, client, charge, reception_headers):
        client.post(
            f"{API}/charges/{charge['id']}/pay",
            json={"payment_method": "pix"},
            headers=reception_headers,
        )
        response = client.post(
            f"{API}/charges/{charge['id']}/pay",
            json={"payment_method": "cash"},
            headers=reception_headers,
        )
        assert response.status_code == 409
        assert "ja foi paga" in response.json()["error"]["message"]

    def test_rejects_wrong_amount(self, client, charge, reception_headers):
        response = client.post(
            f"{API}/charges/{charge['id']}/pay",
            json={"payment_method": "cash", "amount": "100.00"},
            headers=reception_headers,
        )
        assert response.status_code == 422

    def test_accepts_exact_amount(self, client, charge, reception_headers):
        response = client.post(
            f"{API}/charges/{charge['id']}/pay",
            json={"payment_method": "cash", "amount": "240.00"},
            headers=reception_headers,
        )
        assert response.status_code == 200

    def test_cannot_pay_cancelled_charge(self, client, charge, reception_headers):
        client.post(
            f"{API}/charges/{charge['id']}/cancel",
            json={"reason": "Erro"},
            headers=reception_headers,
        )
        response = client.post(
            f"{API}/charges/{charge['id']}/pay",
            json={"payment_method": "pix"},
            headers=reception_headers,
        )
        assert response.status_code == 409

    def test_cannot_cancel_paid_charge(self, client, charge, reception_headers):
        client.post(
            f"{API}/charges/{charge['id']}/pay",
            json={"payment_method": "pix"},
            headers=reception_headers,
        )
        response = client.post(
            f"{API}/charges/{charge['id']}/cancel",
            json={"reason": "Arrependimento"},
            headers=reception_headers,
        )
        assert response.status_code == 409

    def test_patient_cannot_pay(self, client, charge, patient_headers):
        response = client.post(
            f"{API}/charges/{charge['id']}/pay",
            json={"payment_method": "pix"},
            headers=patient_headers,
        )
        assert response.status_code == 403

    def test_unknown_charge_returns_404(self, client, reception_headers):
        response = client.post(
            f"{API}/charges/9999/pay",
            json={"payment_method": "pix"},
            headers=reception_headers,
        )
        assert response.status_code == 404


class TestChargeAccess:
    def test_patient_sees_only_own_charges(self, client, scenario, reception_headers, patient_headers):
        appointment = book(client, reception_headers, scenario)
        client.post(
            f"{API}/charges",
            json={"charge_type": "appointment", "appointment_id": appointment["id"]},
            headers=reception_headers,
        )
        other_appointment = book(
            client, reception_headers, scenario, patient_key="other_patient", hour=10
        )
        client.post(
            f"{API}/charges",
            json={"charge_type": "appointment", "appointment_id": other_appointment["id"]},
            headers=reception_headers,
        )
        response = client.get(f"{API}/charges", headers=patient_headers)
        assert response.json()["meta"]["total"] == 1

    def test_patient_cannot_read_other_charge(self, client, scenario, reception_headers, patient_headers):
        other_appointment = book(
            client, reception_headers, scenario, patient_key="other_patient", hour=10
        )
        charge = client.post(
            f"{API}/charges",
            json={"charge_type": "appointment", "appointment_id": other_appointment["id"]},
            headers=reception_headers,
        ).json()
        response = client.get(f"{API}/charges/{charge['id']}", headers=patient_headers)
        assert response.status_code == 403

    def test_doctor_has_no_billing_access(self, client, scenario, doctor_headers):
        response = client.get(f"{API}/charges", headers=doctor_headers)
        assert response.status_code == 403

    def test_filter_by_status(self, client, scenario, reception_headers):
        appointment = book(client, reception_headers, scenario)
        charge = client.post(
            f"{API}/charges",
            json={"charge_type": "appointment", "appointment_id": appointment["id"]},
            headers=reception_headers,
        ).json()
        client.post(
            f"{API}/charges/{charge['id']}/pay",
            json={"payment_method": "pix"},
            headers=reception_headers,
        )
        paid = client.get(
            f"{API}/charges", params={"status": "paid"}, headers=reception_headers
        ).json()
        pending = client.get(
            f"{API}/charges", params={"status": "pending"}, headers=reception_headers
        ).json()
        assert paid["meta"]["total"] == 1
        assert pending["meta"]["total"] == 0
