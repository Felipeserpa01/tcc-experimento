from tests.conftest import auth_header, next_available_datetime


def _create_and_pay(client, receptionist_token, patient_record, doctor_professional, amount="100.00"):
    scheduled_at = next_available_datetime(doctor_professional)
    appt_response = client.post(
        "/appointments",
        json={
            "patient_id": patient_record.id,
            "doctor_id": doctor_professional.id,
            "scheduled_at": scheduled_at.isoformat(),
            "duration_minutes": 30,
        },
        headers=auth_header(receptionist_token),
    )
    appointment_id = appt_response.json()["id"]

    billing_response = client.post(
        "/billing",
        json={"appointment_id": appointment_id, "amount": amount, "payment_method": "pix"},
        headers=auth_header(receptionist_token),
    )
    billing_id = billing_response.json()["id"]
    client.patch(f"/billing/{billing_id}/pay", json={}, headers=auth_header(receptionist_token))
    return appointment_id


def test_appointments_report_requires_admin(client, receptionist_token):
    response = client.get("/reports/appointments", headers=auth_header(receptionist_token))
    assert response.status_code == 403


def test_appointments_report_returns_entries(
    client, admin_token, receptionist_token, patient_record, doctor_professional
):
    _create_and_pay(client, receptionist_token, patient_record, doctor_professional)

    response = client.get("/reports/appointments", headers=auth_header(admin_token))
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_status_summary_report(client, admin_token, receptionist_token, patient_record, doctor_professional):
    _create_and_pay(client, receptionist_token, patient_record, doctor_professional)

    response = client.get("/reports/appointments/status-summary", headers=auth_header(admin_token))
    assert response.status_code == 200
    statuses = {entry["status"] for entry in response.json()}
    assert "agendada" in statuses


def test_billing_report_totals(
    client, admin_token, receptionist_token, patient_record, doctor_professional
):
    _create_and_pay(client, receptionist_token, patient_record, doctor_professional, amount="100.00")

    response = client.get(
        "/reports/billing",
        params={"start": "2020-01-01", "end": "2030-01-01"},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 200
    body = response.json()
    assert float(body["total_final_amount"]) >= 100.0


def test_no_show_rate_report(client, admin_token, receptionist_token, patient_record, doctor_professional):
    appointment_id = _create_and_pay(client, receptionist_token, patient_record, doctor_professional)
    client.patch(
        f"/appointments/{appointment_id}/status",
        json={"status": "faltou"},
        headers=auth_header(receptionist_token),
    )

    response = client.get("/reports/no-show-rate", headers=auth_header(admin_token))
    assert response.status_code == 200
    entry = next(e for e in response.json() if e["doctor_id"] == doctor_professional.id)
    assert entry["no_show_count"] == 1
    assert entry["no_show_rate"] == 100.0


def test_top_patients_report(client, admin_token, receptionist_token, patient_record, doctor_professional):
    _create_and_pay(client, receptionist_token, patient_record, doctor_professional)

    response = client.get("/reports/top-patients", headers=auth_header(admin_token))
    assert response.status_code == 200
    assert response.json()[0]["patient_id"] == patient_record.id
