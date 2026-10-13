"""Integration tests for report/indicator endpoints and their access control."""
from datetime import date, timedelta

from tests.conftest import next_weekday_datetime


def _schedule(client, recepcionista_headers, patient_id, professional_id, when):
    return client.post(
        "/appointments",
        json={
            "patient_id": patient_id,
            "professional_id": professional_id,
            "data_hora": when.isoformat(),
            "duracao_minutos": 30,
        },
        headers=recepcionista_headers,
    ).json()


def _period_covering_next_week():
    today = date.today()
    return today.isoformat(), (today + timedelta(days=8)).isoformat()


def test_appointments_by_status_report(
    client, admin_headers, recepcionista_headers, medico_user_and_headers, patient_user_and_headers
):
    professional, _ = medico_user_and_headers
    patient, _ = patient_user_and_headers
    appt = _schedule(client, recepcionista_headers, patient.id, professional.id, next_weekday_datetime(0, 9, 0))
    client.patch(f"/appointments/{appt['id']}/status", json={"status": "faltou"}, headers=recepcionista_headers)

    date_from, date_to = _period_covering_next_week()
    resp = client.get(
        "/reports/appointments-by-status",
        params={"date_from": date_from, "date_to": date_to},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    statuses = {row["status"]: row["total"] for row in resp.json()}
    assert statuses.get("faltou") == 1


def test_no_show_rate_report(
    client, admin_headers, recepcionista_headers, medico_user_and_headers, patient_user_and_headers
):
    professional, _ = medico_user_and_headers
    patient, _ = patient_user_and_headers

    appt1 = _schedule(client, recepcionista_headers, patient.id, professional.id, next_weekday_datetime(0, 9, 0))
    appt2 = _schedule(client, recepcionista_headers, patient.id, professional.id, next_weekday_datetime(0, 10, 0))
    client.patch(f"/appointments/{appt1['id']}/status", json={"status": "faltou"}, headers=recepcionista_headers)
    client.patch(
        f"/appointments/{appt2['id']}/status", json={"status": "confirmada"}, headers=recepcionista_headers
    )

    date_from, date_to = _period_covering_next_week()
    resp = client.get(
        "/reports/no-show-rate", params={"date_from": date_from, "date_to": date_to}, headers=admin_headers
    )
    assert resp.status_code == 200
    row = next(r for r in resp.json() if r["professional_id"] == professional.id)
    assert row["total_consultas"] == 2
    assert row["total_faltas"] == 1
    assert row["taxa_faltas"] == 50.0


def test_revenue_by_period_report(
    client, admin_headers, recepcionista_headers, medico_user_and_headers, patient_user_and_headers
):
    professional, _ = medico_user_and_headers
    patient, _ = patient_user_and_headers
    appt = _schedule(client, recepcionista_headers, patient.id, professional.id, next_weekday_datetime(0, 9, 0))

    billing = client.post(
        "/billing",
        json={
            "patient_id": patient.id,
            "appointment_id": appt["id"],
            "tipo": "consulta",
            "valor": "250.00",
            "forma_pagamento": "pix",
        },
        headers=recepcionista_headers,
    ).json()
    client.post(f"/billing/{billing['id']}/pay", json={}, headers=recepcionista_headers)

    today = date.today()
    resp = client.get(
        "/reports/revenue-by-period",
        params={"date_from": today.isoformat(), "date_to": today.isoformat()},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert float(body[0]["total"]) == 250.0


def test_top_patients_report(
    client, admin_headers, recepcionista_headers, medico_user_and_headers, patient_user_and_headers
):
    professional, _ = medico_user_and_headers
    patient, _ = patient_user_and_headers
    _schedule(client, recepcionista_headers, patient.id, professional.id, next_weekday_datetime(0, 9, 0))
    _schedule(client, recepcionista_headers, patient.id, professional.id, next_weekday_datetime(0, 10, 0))

    date_from, date_to = _period_covering_next_week()
    resp = client.get(
        "/reports/top-patients", params={"date_from": date_from, "date_to": date_to}, headers=admin_headers
    )
    assert resp.status_code == 200
    top = resp.json()[0]
    assert top["patient_id"] == patient.id
    assert top["total_consultas"] == 2


def test_reports_reject_inverted_period(client, admin_headers):
    today = date.today()
    resp = client.get(
        "/reports/appointments-by-period",
        params={"date_from": today.isoformat(), "date_to": (today - timedelta(days=1)).isoformat()},
        headers=admin_headers,
    )
    assert resp.status_code == 422


def test_reports_forbidden_for_doctor_and_patient(
    client, medico_user_and_headers, patient_user_and_headers
):
    _, doctor_headers = medico_user_and_headers
    _, patient_headers = patient_user_and_headers
    date_from, date_to = _period_covering_next_week()

    for headers in (doctor_headers, patient_headers):
        resp = client.get(
            "/reports/appointments-by-period",
            params={"date_from": date_from, "date_to": date_to},
            headers=headers,
        )
        assert resp.status_code == 403
