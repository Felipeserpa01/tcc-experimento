"""Integration tests for medical records, prescriptions, exams and clinical history access."""
from tests.conftest import VALID_PASSWORD, next_weekday_datetime


def _schedule_and_confirm(client, recepcionista_headers, patient_id, professional_id, when):
    appt = client.post(
        "/appointments",
        json={
            "patient_id": patient_id,
            "professional_id": professional_id,
            "data_hora": when.isoformat(),
            "duracao_minutos": 30,
        },
        headers=recepcionista_headers,
    ).json()
    return appt


def test_responsible_doctor_can_create_medical_record(
    client, recepcionista_headers, medico_user_and_headers, patient_user_and_headers
):
    professional, doctor_headers = medico_user_and_headers
    patient, _ = patient_user_and_headers
    when = next_weekday_datetime(0, 10, 0)
    appt = _schedule_and_confirm(client, recepcionista_headers, patient.id, professional.id, when)

    resp = client.post(
        f"/appointments/{appt['id']}/medical-record",
        json={"queixa": "Dor de cabeça", "diagnostico": "Enxaqueca", "observacoes": "Repouso"},
        headers=doctor_headers,
    )
    assert resp.status_code == 201, resp.text


def test_non_responsible_doctor_cannot_create_medical_record(
    client, admin_headers, recepcionista_headers, medico_user_and_headers, patient_user_and_headers
):
    professional, _ = medico_user_and_headers
    patient, _ = patient_user_and_headers
    when = next_weekday_datetime(1, 10, 0)
    appt = _schedule_and_confirm(client, recepcionista_headers, patient.id, professional.id, when)

    other_doctor_resp = client.post(
        "/professionals",
        json={
            "nome": "Dr. Outro",
            "tipo": "medico",
            "crm": "999888-SP",
            "especialidade": "Clínica Geral",
            "email": "outro.medico@clinica.com",
            "password": VALID_PASSWORD,
        },
        headers=admin_headers,
    )
    assert other_doctor_resp.status_code == 201
    login = client.post(
        "/auth/login", json={"email": "outro.medico@clinica.com", "password": VALID_PASSWORD}
    )
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = client.post(
        f"/appointments/{appt['id']}/medical-record",
        json={"queixa": "Dor", "diagnostico": "Diagnóstico", "observacoes": None},
        headers=other_headers,
    )
    assert resp.status_code == 403


def test_nurse_cannot_create_medical_record(
    client, recepcionista_headers, medico_user_and_headers, enfermeiro_user_and_headers, patient_user_and_headers
):
    professional, _ = medico_user_and_headers
    _, nurse_headers = enfermeiro_user_and_headers
    patient, _ = patient_user_and_headers
    when = next_weekday_datetime(2, 10, 0)
    appt = _schedule_and_confirm(client, recepcionista_headers, patient.id, professional.id, when)

    resp = client.post(
        f"/appointments/{appt['id']}/medical-record",
        json={"queixa": "Dor", "diagnostico": "Diagnóstico"},
        headers=nurse_headers,
    )
    assert resp.status_code == 403


def test_duplicate_medical_record_rejected(
    client, recepcionista_headers, medico_user_and_headers, patient_user_and_headers
):
    professional, doctor_headers = medico_user_and_headers
    patient, _ = patient_user_and_headers
    when = next_weekday_datetime(3, 10, 0)
    appt = _schedule_and_confirm(client, recepcionista_headers, patient.id, professional.id, when)

    payload = {"queixa": "Dor", "diagnostico": "Diagnóstico"}
    first = client.post(f"/appointments/{appt['id']}/medical-record", json=payload, headers=doctor_headers)
    assert first.status_code == 201

    second = client.post(f"/appointments/{appt['id']}/medical-record", json=payload, headers=doctor_headers)
    assert second.status_code == 409


def test_prescription_and_exam_flow(
    client, recepcionista_headers, medico_user_and_headers, patient_user_and_headers
):
    professional, doctor_headers = medico_user_and_headers
    patient, patient_headers = patient_user_and_headers
    when = next_weekday_datetime(4, 10, 0)
    appt = _schedule_and_confirm(client, recepcionista_headers, patient.id, professional.id, when)

    prescription = client.post(
        f"/appointments/{appt['id']}/prescriptions",
        json={"medicamento": "Dipirona", "dosagem": "500mg", "frequencia": "8/8h", "duracao": "5 dias"},
        headers=doctor_headers,
    )
    assert prescription.status_code == 201

    exam = client.post(
        f"/appointments/{appt['id']}/exams", json={"tipo_exame": "Hemograma completo"}, headers=doctor_headers
    )
    assert exam.status_code == 201
    exam_id = exam.json()["id"]
    assert exam.json()["status"] == "solicitado"

    result = client.patch(
        f"/exams/{exam_id}/result", json={"resultado": "Dentro dos parâmetros normais."}, headers=doctor_headers
    )
    assert result.status_code == 200
    assert result.json()["status"] == "resultado_disponivel"

    # Patient can view their own exams and prescriptions, without editing them.
    patient_view = client.get(f"/appointments/{appt['id']}/exams", headers=patient_headers)
    assert patient_view.status_code == 200
    assert len(patient_view.json()) == 1

    patient_cannot_create = client.post(
        f"/appointments/{appt['id']}/exams", json={"tipo_exame": "Outro"}, headers=patient_headers
    )
    assert patient_cannot_create.status_code == 403


def test_patient_can_view_own_clinical_history(
    client, recepcionista_headers, medico_user_and_headers, patient_user_and_headers
):
    professional, doctor_headers = medico_user_and_headers
    patient, patient_headers = patient_user_and_headers
    when = next_weekday_datetime(5, 10, 0)
    appt = _schedule_and_confirm(client, recepcionista_headers, patient.id, professional.id, when)
    client.post(
        f"/appointments/{appt['id']}/medical-record",
        json={"queixa": "Febre", "diagnostico": "Virose"},
        headers=doctor_headers,
    )

    resp = client.get(f"/patients/{patient.id}/history", headers=patient_headers)
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) == 1
    assert history[0]["medical_record"]["diagnostico"] == "Virose"


def test_patient_cannot_view_others_history(
    client, recepcionista_headers, patient_user_and_headers
):
    other = client.post(
        "/patients",
        json={
            "nome": "Terceiro Paciente",
            "cpf": "123.456.789-09",
            "data_nascimento": "1975-03-03",
            "sexo": "Masculino",
            "telefone": "11933332222",
            "email": "terceiro@example.com",
            "endereco_rua": "Rua D",
            "endereco_numero": "20",
            "endereco_bairro": "Centro",
            "endereco_cidade": "São Paulo",
            "endereco_estado": "SP",
            "endereco_cep": "04000000",
        },
        headers=recepcionista_headers,
    ).json()

    _, patient_headers = patient_user_and_headers
    resp = client.get(f"/patients/{other['id']}/history", headers=patient_headers)
    assert resp.status_code == 403


def test_receptionist_cannot_view_clinical_history(client, recepcionista_headers, patient_user_and_headers):
    patient, _ = patient_user_and_headers
    resp = client.get(f"/patients/{patient.id}/history", headers=recepcionista_headers)
    assert resp.status_code == 403
