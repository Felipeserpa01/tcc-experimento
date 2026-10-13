from datetime import timedelta

from tests.conftest import auth_header, next_available_datetime


def _schedule(client, token, patient_id, doctor_id, scheduled_at, duration=30):
    return client.post(
        "/appointments",
        json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "scheduled_at": scheduled_at.isoformat(),
            "duration_minutes": duration,
        },
        headers=auth_header(token),
    )


def test_schedule_appointment_success(client, receptionist_token, patient_record, doctor_professional):
    scheduled_at = next_available_datetime(doctor_professional)
    response = _schedule(
        client, receptionist_token, patient_record.id, doctor_professional.id, scheduled_at
    )
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "agendada"


def test_schedule_rejects_past_datetime(client, receptionist_token, patient_record, doctor_professional):
    from datetime import datetime, timezone

    past = datetime.now(timezone.utc) - timedelta(days=1)
    response = _schedule(client, receptionist_token, patient_record.id, doctor_professional.id, past)
    assert response.status_code == 422


def test_schedule_rejects_outside_availability(
    client, receptionist_token, patient_record, doctor_professional
):
    scheduled_at = next_available_datetime(doctor_professional).replace(hour=23)
    response = _schedule(
        client, receptionist_token, patient_record.id, doctor_professional.id, scheduled_at
    )
    assert response.status_code == 422


def test_schedule_detects_doctor_conflict(
    client, receptionist_token, patient_record, doctor_professional
):
    scheduled_at = next_available_datetime(doctor_professional)
    first = _schedule(
        client, receptionist_token, patient_record.id, doctor_professional.id, scheduled_at
    )
    assert first.status_code == 201

    second = _schedule(
        client, receptionist_token, patient_record.id, doctor_professional.id, scheduled_at
    )
    assert second.status_code == 409


def test_patient_can_only_schedule_for_self(
    client, patient_token, receptionist_token, doctor_professional
):
    other_patient_payload = {
        "full_name": "Outro Paciente",
        "cpf": "390.533.447-05",
        "birth_date": "1980-01-01",
        "sex": "M",
        "phone": "11966665555",
        "address_street": "Rua B",
        "address_number": "10",
        "address_neighborhood": "Centro",
        "address_city": "São Paulo",
        "address_state": "SP",
        "address_zip_code": "01000-000",
    }
    other_response = client.post(
        "/patients", json=other_patient_payload, headers=auth_header(receptionist_token)
    )
    other_patient_id = other_response.json()["id"]

    scheduled_at = next_available_datetime(doctor_professional)
    response = _schedule(client, patient_token, other_patient_id, doctor_professional.id, scheduled_at)
    assert response.status_code == 403


def test_confirm_and_cancel_appointment(
    client, receptionist_token, patient_record, doctor_professional
):
    scheduled_at = next_available_datetime(doctor_professional)
    create_response = _schedule(
        client, receptionist_token, patient_record.id, doctor_professional.id, scheduled_at
    )
    appointment_id = create_response.json()["id"]

    confirm_response = client.patch(
        f"/appointments/{appointment_id}/confirm", headers=auth_header(receptionist_token)
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == "confirmada"

    cancel_response = client.patch(
        f"/appointments/{appointment_id}/cancel",
        json={"reason": "Paciente solicitou cancelamento"},
        headers=auth_header(receptionist_token),
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelada"
    assert cancel_response.json()["cancellation_reason"] == "Paciente solicitou cancelamento"


def test_cannot_confirm_already_cancelled_appointment(
    client, receptionist_token, patient_record, doctor_professional
):
    scheduled_at = next_available_datetime(doctor_professional)
    create_response = _schedule(
        client, receptionist_token, patient_record.id, doctor_professional.id, scheduled_at
    )
    appointment_id = create_response.json()["id"]

    client.patch(
        f"/appointments/{appointment_id}/cancel",
        json={"reason": "motivo qualquer"},
        headers=auth_header(receptionist_token),
    )

    response = client.patch(
        f"/appointments/{appointment_id}/confirm", headers=auth_header(receptionist_token)
    )
    assert response.status_code == 409


def test_reschedule_appointment(client, receptionist_token, patient_record, doctor_professional):
    scheduled_at = next_available_datetime(doctor_professional)
    create_response = _schedule(
        client, receptionist_token, patient_record.id, doctor_professional.id, scheduled_at
    )
    appointment_id = create_response.json()["id"]

    new_time = scheduled_at + timedelta(hours=1)
    response = client.patch(
        f"/appointments/{appointment_id}/reschedule",
        json={"scheduled_at": new_time.isoformat()},
        headers=auth_header(receptionist_token),
    )
    assert response.status_code == 200
    assert response.json()["scheduled_at"].startswith(new_time.isoformat()[:16])


def test_join_waitlist(client, patient_token, patient_record, doctor_professional):
    response = client.post(
        "/appointments/waitlist",
        json={
            "patient_id": patient_record.id,
            "doctor_id": doctor_professional.id,
            "desired_date": "2027-01-15",
        },
        headers=auth_header(patient_token),
    )
    assert response.status_code == 201, response.text
    assert response.json()["notified"] is False


def test_doctor_day_agenda(client, receptionist_token, patient_record, doctor_professional):
    scheduled_at = next_available_datetime(doctor_professional)
    _schedule(client, receptionist_token, patient_record.id, doctor_professional.id, scheduled_at)

    response = client.get(
        f"/appointments/doctor/{doctor_professional.id}/day",
        params={"day": scheduled_at.date().isoformat()},
        headers=auth_header(receptionist_token),
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_no_show_status_update(client, receptionist_token, patient_record, doctor_professional):
    scheduled_at = next_available_datetime(doctor_professional)
    create_response = _schedule(
        client, receptionist_token, patient_record.id, doctor_professional.id, scheduled_at
    )
    appointment_id = create_response.json()["id"]

    response = client.patch(
        f"/appointments/{appointment_id}/status",
        json={"status": "faltou"},
        headers=auth_header(receptionist_token),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "faltou"
