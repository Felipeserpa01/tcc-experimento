"""Integration tests for appointment scheduling, conflicts, availability, waitlist and status flow."""
from datetime import date, datetime, time, timedelta

from tests.conftest import next_weekday_datetime


def _schedule(client, headers, patient_id, professional_id, when: datetime, duracao=30):
    return client.post(
        "/appointments",
        json={
            "patient_id": patient_id,
            "professional_id": professional_id,
            "data_hora": when.isoformat(),
            "duracao_minutos": duracao,
        },
        headers=headers,
    )


def test_schedule_appointment_within_availability_succeeds(
    client, recepcionista_headers, medico_user_and_headers, patient_user_and_headers
):
    professional, _ = medico_user_and_headers
    patient, _ = patient_user_and_headers
    when = next_weekday_datetime(0, 10, 0)

    resp = _schedule(client, recepcionista_headers, patient.id, professional.id, when)
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "agendada"


def test_schedule_appointment_past_date_rejected(
    client, recepcionista_headers, medico_user_and_headers, patient_user_and_headers
):
    professional, _ = medico_user_and_headers
    patient, _ = patient_user_and_headers
    past = datetime.combine(date.today() - timedelta(days=1), time(10, 0))

    resp = _schedule(client, recepcionista_headers, patient.id, professional.id, past)
    assert resp.status_code == 422


def test_schedule_appointment_conflict_rejected(
    client, recepcionista_headers, medico_user_and_headers, patient_user_and_headers
):
    professional, _ = medico_user_and_headers
    patient, _ = patient_user_and_headers
    when = next_weekday_datetime(1, 10, 0)

    first = _schedule(client, recepcionista_headers, patient.id, professional.id, when)
    assert first.status_code == 201

    second = _schedule(client, recepcionista_headers, patient.id, professional.id, when)
    assert second.status_code == 422
    assert "horário" in second.json()["detail"].lower()


def test_schedule_appointment_outside_availability_rejected(
    client, admin_headers, recepcionista_headers, patient_user_and_headers
):
    doctor = client.post(
        "/professionals",
        json={
            "nome": "Dr. Restrito",
            "tipo": "medico",
            "crm": "111222-SP",
            "especialidade": "Ortopedia",
            "email": "restrito@clinica.com",
            "password": "SenhaForte123!",
        },
        headers=admin_headers,
    ).json()
    client.post(
        f"/professionals/{doctor['id']}/availability",
        json={"dia_semana": 0, "hora_inicio": "08:00:00", "hora_fim": "12:00:00"},
        headers=admin_headers,
    )
    patient, _ = patient_user_and_headers

    # Monday at 14:00 is outside the 08:00-12:00 window.
    outside = next_weekday_datetime(0, 14, 0)
    resp = _schedule(client, recepcionista_headers, patient.id, doctor["id"], outside)
    assert resp.status_code == 422
    assert "fora da agenda" in resp.json()["detail"].lower()

    # Tuesday has no availability slot registered at all.
    no_slot_day = next_weekday_datetime(1, 9, 0)
    resp2 = _schedule(client, recepcionista_headers, patient.id, doctor["id"], no_slot_day)
    assert resp2.status_code == 422


def test_patient_can_only_book_for_self(
    client, recepcionista_headers, medico_user_and_headers, patient_user_and_headers
):
    professional, _ = medico_user_and_headers
    patient, patient_headers = patient_user_and_headers

    other_patient = client.post(
        "/patients",
        json={
            "nome": "Outro Paciente",
            "cpf": "123.456.789-09",
            "data_nascimento": "1980-01-01",
            "sexo": "Masculino",
            "telefone": "11977776666",
            "email": "outro.paciente@example.com",
            "endereco_rua": "Rua B",
            "endereco_numero": "50",
            "endereco_bairro": "Centro",
            "endereco_cidade": "São Paulo",
            "endereco_estado": "SP",
            "endereco_cep": "02000000",
        },
        headers=recepcionista_headers,
    ).json()

    when = next_weekday_datetime(2, 10, 0)
    resp = _schedule(client, patient_headers, other_patient["id"], professional.id, when)
    assert resp.status_code == 403


def test_confirm_and_cancel_appointment(
    client, recepcionista_headers, medico_user_and_headers, patient_user_and_headers
):
    professional, _ = medico_user_and_headers
    patient, _ = patient_user_and_headers
    when = next_weekday_datetime(3, 10, 0)

    appt = _schedule(client, recepcionista_headers, patient.id, professional.id, when).json()

    confirm = client.post(f"/appointments/{appt['id']}/confirm", headers=recepcionista_headers)
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "confirmada"

    cancel = client.post(
        f"/appointments/{appt['id']}/cancel",
        json={"motivo": "Paciente solicitou remarcação"},
        headers=recepcionista_headers,
    )
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelada"


def test_cancel_terminal_appointment_rejected(
    client, recepcionista_headers, medico_user_and_headers, patient_user_and_headers
):
    professional, _ = medico_user_and_headers
    patient, _ = patient_user_and_headers
    when = next_weekday_datetime(4, 10, 0)

    appt = _schedule(client, recepcionista_headers, patient.id, professional.id, when).json()
    client.post(
        f"/appointments/{appt['id']}/cancel", json={"motivo": "motivo qualquer"}, headers=recepcionista_headers
    )

    second_cancel = client.post(
        f"/appointments/{appt['id']}/cancel", json={"motivo": "outro motivo"}, headers=recepcionista_headers
    )
    assert second_cancel.status_code == 422


def test_invalid_status_transition_rejected(
    client, recepcionista_headers, medico_user_and_headers, patient_user_and_headers
):
    professional, _ = medico_user_and_headers
    patient, _ = patient_user_and_headers
    when = next_weekday_datetime(5, 10, 0)

    appt = _schedule(client, recepcionista_headers, patient.id, professional.id, when).json()

    resp = client.patch(
        f"/appointments/{appt['id']}/status", json={"status": "realizada"}, headers=recepcionista_headers
    )
    assert resp.status_code == 422


def test_reschedule_appointment_to_conflicting_slot_rejected(
    client, recepcionista_headers, medico_user_and_headers, patient_user_and_headers
):
    professional, _ = medico_user_and_headers
    patient, _ = patient_user_and_headers
    slot_a = next_weekday_datetime(0, 9, 0)
    slot_b = next_weekday_datetime(0, 11, 0)

    appt_a = _schedule(client, recepcionista_headers, patient.id, professional.id, slot_a).json()
    _schedule(client, recepcionista_headers, patient.id, professional.id, slot_b)

    resp = client.put(
        f"/appointments/{appt_a['id']}/reschedule",
        json={"data_hora": slot_b.isoformat()},
        headers=recepcionista_headers,
    )
    assert resp.status_code == 422


def test_daily_agenda_lists_appointments_for_professional(
    client, recepcionista_headers, medico_user_and_headers, patient_user_and_headers
):
    professional, _ = medico_user_and_headers
    patient, _ = patient_user_and_headers
    when = next_weekday_datetime(0, 9, 0)
    _schedule(client, recepcionista_headers, patient.id, professional.id, when)

    resp = client.get(
        f"/professionals/{professional.id}/agenda", params={"day": when.date().isoformat()},
        headers=recepcionista_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_waitlist_join_and_notification_on_cancel(
    client, recepcionista_headers, medico_user_and_headers, patient_user_and_headers, db_session
):
    from app.models.patient import Patient

    professional, _ = medico_user_and_headers
    patient, _ = patient_user_and_headers
    when = next_weekday_datetime(0, 10, 0)

    booked = _schedule(client, recepcionista_headers, patient.id, professional.id, when).json()

    waitlist_patient = Patient(
        nome="Paciente Espera",
        cpf="12345678909",
        data_nascimento=date(1992, 2, 2),
        sexo="Feminino",
        telefone="11955554444",
        email="espera@example.com",
        endereco_rua="Rua C",
        endereco_numero="10",
        endereco_bairro="Centro",
        endereco_cidade="São Paulo",
        endereco_estado="SP",
        endereco_cep="03000000",
    )
    db_session.add(waitlist_patient)
    db_session.commit()
    db_session.refresh(waitlist_patient)

    wl_resp = client.post(
        "/waitlist",
        json={
            "patient_id": waitlist_patient.id,
            "professional_id": professional.id,
            "data_desejada": when.date().isoformat(),
        },
        headers=recepcionista_headers,
    )
    assert wl_resp.status_code == 201
    assert wl_resp.json()["status"] == "aguardando"

    cancel = client.post(
        f"/appointments/{booked['id']}/cancel",
        json={"motivo": "Paciente cancelou"},
        headers=recepcionista_headers,
    )
    assert cancel.status_code == 200

    db_session.expire_all()
    from app.models.appointment import WaitlistEntry

    entry = db_session.query(WaitlistEntry).filter(WaitlistEntry.id == wl_resp.json()["id"]).first()
    assert entry.status.value == "notificado"
    assert entry.notified_at is not None
