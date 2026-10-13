"""Testes dos relatorios e indicadores."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.models.appointment import Appointment
from tests.conftest import API, auth_headers, next_weekday_at, past_datetime


@pytest.fixture()
def reception_headers(client, scenario):
    return auth_headers(client, "recepcao@clinica.com")


@pytest.fixture()
def admin_headers(client, scenario):
    return auth_headers(client, "admin@clinica.com")


@pytest.fixture()
def doctor_headers(client, scenario):
    return auth_headers(client, "medico@clinica.com")


def book(client, headers, scenario, *, patient_key="patient", professional_key="doctor", hour=9):
    return client.post(
        f"{API}/appointments",
        json={
            "patient_id": scenario[patient_key].id,
            "professional_id": scenario[professional_key].id,
            "scheduled_start": next_weekday_at(hour).isoformat(),
        },
        headers=headers,
    ).json()


@pytest.fixture()
def populated(client, db, scenario, reception_headers, doctor_headers):
    """Cria consultas em varios status e uma cobranca paga."""
    completed = book(client, reception_headers, scenario, hour=9)
    client.post(f"{API}/appointments/{completed['id']}/start", headers=doctor_headers)
    client.post(f"{API}/appointments/{completed['id']}/complete", headers=doctor_headers)

    cancelled = book(client, reception_headers, scenario, hour=10)
    client.post(
        f"{API}/appointments/{cancelled['id']}/cancel",
        json={"reason": "Desistencia"},
        headers=reception_headers,
    )

    no_show = book(client, reception_headers, scenario, patient_key="other_patient", hour=11)
    stored = db.get(Appointment, no_show["id"])
    stored.scheduled_start = past_datetime()
    stored.scheduled_end = past_datetime() + timedelta(minutes=30)
    db.commit()
    client.post(f"{API}/appointments/{no_show['id']}/no-show", headers=reception_headers)

    other_specialty = book(
        client,
        reception_headers,
        scenario,
        patient_key="other_patient",
        professional_key="other_doctor",
        hour=14,
    )

    charge = client.post(
        f"{API}/charges",
        json={"charge_type": "appointment", "appointment_id": completed["id"]},
        headers=reception_headers,
    ).json()
    client.post(
        f"{API}/charges/{charge['id']}/pay",
        json={"payment_method": "pix"},
        headers=reception_headers,
    )
    pending_charge = client.post(
        f"{API}/charges",
        json={"charge_type": "appointment", "appointment_id": other_specialty["id"]},
        headers=reception_headers,
    ).json()

    return {
        "completed": completed,
        "cancelled": cancelled,
        "no_show": no_show,
        "other_specialty": other_specialty,
        "paid_charge": charge,
        "pending_charge": pending_charge,
    }


class TestAppointmentsReport:
    def test_totals_by_status(self, client, populated, admin_headers):
        response = client.get(f"{API}/reports/appointments", headers=admin_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["total_appointments"] == 4
        statuses = {item["status"]: item["total"] for item in body["by_status"]}
        assert statuses["completed"] == 1
        assert statuses["cancelled"] == 1
        assert statuses["no_show"] == 1
        assert statuses["scheduled"] == 1

    def test_percentages_sum_to_100(self, client, populated, admin_headers):
        body = client.get(f"{API}/reports/appointments", headers=admin_headers).json()
        total_percentage = sum(item["percentage"] for item in body["by_status"])
        assert round(total_percentage) == 100

    def test_by_professional(self, client, populated, scenario, admin_headers):
        body = client.get(f"{API}/reports/appointments", headers=admin_headers).json()
        by_professional = {
            item["professional_id"]: item["total"] for item in body["by_professional"]
        }
        assert by_professional[scenario["doctor"].id] == 3
        assert by_professional[scenario["other_doctor"].id] == 1

    def test_by_specialty(self, client, populated, admin_headers):
        body = client.get(f"{API}/reports/appointments", headers=admin_headers).json()
        by_specialty = {item["specialty"]: item["total"] for item in body["by_specialty"]}
        assert by_specialty["Cardiologia"] == 3
        assert by_specialty["Dermatologia"] == 1

    def test_filter_by_specialty(self, client, populated, admin_headers):
        body = client.get(
            f"{API}/reports/appointments",
            params={"specialty": "Dermato"},
            headers=admin_headers,
        ).json()
        assert body["total_appointments"] == 1

    def test_filter_by_professional(self, client, populated, scenario, admin_headers):
        body = client.get(
            f"{API}/reports/appointments",
            params={"professional_id": scenario["other_doctor"].id},
            headers=admin_headers,
        ).json()
        assert body["total_appointments"] == 1

    def test_period_filter_excludes_everything(self, client, populated, admin_headers):
        body = client.get(
            f"{API}/reports/appointments",
            params={"start_date": "2000-01-01", "end_date": "2000-12-31"},
            headers=admin_headers,
        ).json()
        assert body["total_appointments"] == 0

    def test_doctor_is_scoped_to_own_data(self, client, populated, doctor_headers):
        body = client.get(f"{API}/reports/appointments", headers=doctor_headers).json()
        assert body["total_appointments"] == 3

    def test_doctor_cannot_query_colleague(self, client, populated, scenario, doctor_headers):
        response = client.get(
            f"{API}/reports/appointments",
            params={"professional_id": scenario["other_doctor"].id},
            headers=doctor_headers,
        )
        assert response.status_code == 403

    def test_patient_has_no_access(self, client, populated):
        headers = auth_headers(client, "paciente@clinica.com")
        response = client.get(f"{API}/reports/appointments", headers=headers)
        assert response.status_code == 403


class TestRevenueReport:
    def test_totals(self, client, populated, admin_headers):
        body = client.get(f"{API}/reports/revenue", headers=admin_headers).json()
        assert body["total_received"] == "240.00"
        assert body["total_pending"] == "300.00"
        assert body["total_billed"] == "540.00"
        assert body["total_discounts"] == "60.00"

    def test_by_payment_method(self, client, populated, admin_headers):
        body = client.get(f"{API}/reports/revenue", headers=admin_headers).json()
        methods = {item["payment_method"]: item["total_amount"] for item in body["by_payment_method"]}
        assert methods["pix"] == "240.00"

    def test_by_status(self, client, populated, admin_headers):
        body = client.get(f"{API}/reports/revenue", headers=admin_headers).json()
        statuses = {item["status"]: item["total_charges"] for item in body["by_status"]}
        assert statuses["paid"] == 1
        assert statuses["pending"] == 1

    def test_filter_by_payment_method(self, client, populated, admin_headers):
        body = client.get(
            f"{API}/reports/revenue", params={"payment_method": "cash"}, headers=admin_headers
        ).json()
        assert body["total_received"] == "0.00"

    def test_receptionist_has_access(self, client, populated, reception_headers):
        assert client.get(f"{API}/reports/revenue", headers=reception_headers).status_code == 200

    def test_doctor_has_no_financial_access(self, client, populated, doctor_headers):
        response = client.get(f"{API}/reports/revenue", headers=doctor_headers)
        assert response.status_code == 403


class TestNoShowReport:
    def test_rate_by_professional(self, client, populated, scenario, admin_headers):
        body = client.get(f"{API}/reports/no-show", headers=admin_headers).json()
        by_professional = {
            item["professional_id"]: item for item in body["by_professional"]
        }
        cardio = by_professional[scenario["doctor"].id]
        # 2 consultas nao canceladas, sendo 1 falta -> 50%
        assert cardio["total_appointments"] == 2
        assert cardio["no_show_count"] == 1
        assert cardio["no_show_rate_percent"] == 50.0

    def test_overall_rate(self, client, populated, admin_headers):
        body = client.get(f"{API}/reports/no-show", headers=admin_headers).json()
        assert body["overall_total"] == 3
        assert body["overall_no_show"] == 1
        assert body["overall_rate_percent"] == 33.33

    def test_patient_has_no_access(self, client, populated):
        headers = auth_headers(client, "paciente@clinica.com")
        assert client.get(f"{API}/reports/no-show", headers=headers).status_code == 403


class TestTopPatientsReport:
    def test_ranking(self, client, populated, scenario, admin_headers):
        body = client.get(f"{API}/reports/top-patients", headers=admin_headers).json()
        items = {item["patient_id"]: item for item in body["items"]}
        assert items[scenario["patient"].id]["total_appointments"] == 1
        assert items[scenario["patient"].id]["completed_appointments"] == 1
        assert items[scenario["other_patient"].id]["total_appointments"] == 2

    def test_limit_is_respected(self, client, populated, admin_headers):
        body = client.get(
            f"{API}/reports/top-patients", params={"limit": 1}, headers=admin_headers
        ).json()
        assert len(body["items"]) == 1

    def test_ordered_by_volume(self, client, populated, admin_headers):
        body = client.get(f"{API}/reports/top-patients", headers=admin_headers).json()
        totals = [item["total_appointments"] for item in body["items"]]
        assert totals == sorted(totals, reverse=True)

    def test_report_generation_is_audited(self, client, populated, admin_headers):
        client.get(f"{API}/reports/top-patients", headers=admin_headers)
        logs = client.get(
            f"{API}/audit-logs", params={"action": "report."}, headers=admin_headers
        ).json()
        assert logs["meta"]["total"] >= 1
