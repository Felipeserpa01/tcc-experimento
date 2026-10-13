from tests.conftest import auth_header, next_available_datetime


def _schedule_and_start(client, receptionist_token, doctor_token, patient_record, doctor_professional):
    scheduled_at = next_available_datetime(doctor_professional)
    create_response = client.post(
        "/appointments",
        json={
            "patient_id": patient_record.id,
            "doctor_id": doctor_professional.id,
            "scheduled_at": scheduled_at.isoformat(),
            "duration_minutes": 30,
        },
        headers=auth_header(receptionist_token),
    )
    appointment_id = create_response.json()["id"]

    client.patch(f"/appointments/{appointment_id}/confirm", headers=auth_header(receptionist_token))
    client.patch(
        f"/appointments/{appointment_id}/status",
        json={"status": "em_andamento"},
        headers=auth_header(doctor_token),
    )
    return appointment_id


def test_responsible_doctor_creates_medical_record(
    client, receptionist_token, doctor_token, patient_record, doctor_professional
):
    appointment_id = _schedule_and_start(
        client, receptionist_token, doctor_token, patient_record, doctor_professional
    )

    response = client.post(
        f"/appointments/{appointment_id}/medical-record",
        json={"complaint": "Dor no peito", "diagnosis": "Ansiedade", "notes": "Encaminhar para exames"},
        headers=auth_header(doctor_token),
    )
    assert response.status_code == 201, response.text
    assert response.json()["diagnosis"] == "Ansiedade"

    appointment_response = client.get(
        f"/appointments/{appointment_id}", headers=auth_header(doctor_token)
    )
    assert appointment_response.json()["status"] == "realizada"


def test_nurse_cannot_create_medical_record(
    client, db_session, receptionist_token, doctor_token, patient_record, doctor_professional
):
    from app.core.security import hash_password
    from app.models.enums import UserRole
    from app.models.user import User

    nurse_user = User(email="enfermeiro@clinica.com", hashed_password=hash_password("Senha123!"), role=UserRole.NURSE)
    db_session.add(nurse_user)
    db_session.commit()
    nurse_login = client.post(
        "/auth/login", json={"email": "enfermeiro@clinica.com", "password": "Senha123!"}
    )
    nurse_token = nurse_login.json()["access_token"]

    appointment_id = _schedule_and_start(
        client, receptionist_token, doctor_token, patient_record, doctor_professional
    )

    response = client.post(
        f"/appointments/{appointment_id}/medical-record",
        json={"complaint": "x", "diagnosis": "y"},
        headers=auth_header(nurse_token),
    )
    assert response.status_code == 403


def test_cannot_create_duplicate_medical_record_for_appointment(
    client, receptionist_token, doctor_token, patient_record, doctor_professional
):
    appointment_id = _schedule_and_start(
        client, receptionist_token, doctor_token, patient_record, doctor_professional
    )
    payload = {"complaint": "Dor", "diagnosis": "Diagnóstico"}
    client.post(
        f"/appointments/{appointment_id}/medical-record",
        json=payload,
        headers=auth_header(doctor_token),
    )
    response = client.post(
        f"/appointments/{appointment_id}/medical-record",
        json=payload,
        headers=auth_header(doctor_token),
    )
    assert response.status_code == 409


def test_add_prescription_and_exam(
    client, receptionist_token, doctor_token, patient_record, doctor_professional
):
    appointment_id = _schedule_and_start(
        client, receptionist_token, doctor_token, patient_record, doctor_professional
    )
    record_response = client.post(
        f"/appointments/{appointment_id}/medical-record",
        json={"complaint": "Dor", "diagnosis": "Diagnóstico"},
        headers=auth_header(doctor_token),
    )
    record_id = record_response.json()["id"]

    prescription_response = client.post(
        f"/medical-records/{record_id}/prescriptions",
        json={
            "medication_name": "Dipirona",
            "dosage": "500mg",
            "frequency": "a cada 8 horas",
            "duration": "5 dias",
        },
        headers=auth_header(doctor_token),
    )
    assert prescription_response.status_code == 201

    exam_response = client.post(
        f"/medical-records/{record_id}/exams",
        json={"exam_name": "Hemograma"},
        headers=auth_header(doctor_token),
    )
    assert exam_response.status_code == 201
    exam_id = exam_response.json()["id"]

    result_response = client.patch(
        f"/exams/{exam_id}/result",
        json={"result": "Dentro dos parâmetros normais"},
        headers=auth_header(doctor_token),
    )
    assert result_response.status_code == 200
    assert result_response.json()["result"] == "Dentro dos parâmetros normais"


def test_patient_can_view_own_history_read_only(
    client, receptionist_token, doctor_token, patient_token, patient_record, doctor_professional
):
    appointment_id = _schedule_and_start(
        client, receptionist_token, doctor_token, patient_record, doctor_professional
    )
    client.post(
        f"/appointments/{appointment_id}/medical-record",
        json={"complaint": "Dor", "diagnosis": "Diagnóstico"},
        headers=auth_header(doctor_token),
    )

    response = client.get(
        f"/patients/{patient_record.id}/history", headers=auth_header(patient_token)
    )
    assert response.status_code == 200
    history = response.json()
    assert len(history) == 1
    assert history[0]["medical_record"]["diagnosis"] == "Diagnóstico"

    forbidden_write = client.post(
        f"/medical-records/{history[0]['medical_record']['id']}/prescriptions",
        json={"medication_name": "x", "dosage": "x", "frequency": "x", "duration": "x"},
        headers=auth_header(patient_token),
    )
    assert forbidden_write.status_code == 403
