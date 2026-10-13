from tests.conftest import auth_header, next_available_datetime


def _create_appointment(client, receptionist_token, patient_record, doctor_professional):
    scheduled_at = next_available_datetime(doctor_professional)
    response = client.post(
        "/appointments",
        json={
            "patient_id": patient_record.id,
            "doctor_id": doctor_professional.id,
            "scheduled_at": scheduled_at.isoformat(),
            "duration_minutes": 30,
        },
        headers=auth_header(receptionist_token),
    )
    return response.json()["id"]


def test_create_billing_without_insurance(
    client, receptionist_token, patient_record, doctor_professional, db_session
):
    patient_record.insurance = None
    db_session.commit()

    appointment_id = _create_appointment(client, receptionist_token, patient_record, doctor_professional)
    response = client.post(
        "/billing",
        json={"appointment_id": appointment_id, "amount": "200.00", "payment_method": "pix"},
        headers=auth_header(receptionist_token),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["discount"] == "0.00"
    assert body["final_amount"] == "200.00"


def test_create_billing_applies_insurance_discount(
    client, receptionist_token, patient_record, doctor_professional, db_session
):
    patient_record.insurance = "Unimed"
    db_session.commit()

    appointment_id = _create_appointment(client, receptionist_token, patient_record, doctor_professional)
    response = client.post(
        "/billing",
        json={"appointment_id": appointment_id, "amount": "200.00", "payment_method": "convenio"},
        headers=auth_header(receptionist_token),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["discount"] == "60.00"
    assert body["final_amount"] == "140.00"


def test_pay_billing_success(client, receptionist_token, patient_record, doctor_professional):
    appointment_id = _create_appointment(client, receptionist_token, patient_record, doctor_professional)
    create_response = client.post(
        "/billing",
        json={"appointment_id": appointment_id, "amount": "150.00", "payment_method": "dinheiro"},
        headers=auth_header(receptionist_token),
    )
    billing_id = create_response.json()["id"]

    pay_response = client.patch(
        f"/billing/{billing_id}/pay", json={}, headers=auth_header(receptionist_token)
    )
    assert pay_response.status_code == 200
    assert pay_response.json()["status"] == "pago"


def test_cannot_pay_already_paid_billing(client, receptionist_token, patient_record, doctor_professional):
    appointment_id = _create_appointment(client, receptionist_token, patient_record, doctor_professional)
    create_response = client.post(
        "/billing",
        json={"appointment_id": appointment_id, "amount": "150.00", "payment_method": "dinheiro"},
        headers=auth_header(receptionist_token),
    )
    billing_id = create_response.json()["id"]

    client.patch(f"/billing/{billing_id}/pay", json={}, headers=auth_header(receptionist_token))
    second_pay = client.patch(
        f"/billing/{billing_id}/pay", json={}, headers=auth_header(receptionist_token)
    )
    assert second_pay.status_code == 409


def test_cancel_billing(client, receptionist_token, patient_record, doctor_professional):
    appointment_id = _create_appointment(client, receptionist_token, patient_record, doctor_professional)
    create_response = client.post(
        "/billing",
        json={"appointment_id": appointment_id, "amount": "150.00", "payment_method": "dinheiro"},
        headers=auth_header(receptionist_token),
    )
    billing_id = create_response.json()["id"]

    response = client.patch(f"/billing/{billing_id}/cancel", headers=auth_header(receptionist_token))
    assert response.status_code == 200
    assert response.json()["status"] == "cancelado"


def test_cannot_cancel_paid_billing(client, receptionist_token, patient_record, doctor_professional):
    appointment_id = _create_appointment(client, receptionist_token, patient_record, doctor_professional)
    create_response = client.post(
        "/billing",
        json={"appointment_id": appointment_id, "amount": "150.00", "payment_method": "dinheiro"},
        headers=auth_header(receptionist_token),
    )
    billing_id = create_response.json()["id"]

    client.patch(f"/billing/{billing_id}/pay", json={}, headers=auth_header(receptionist_token))
    response = client.patch(f"/billing/{billing_id}/cancel", headers=auth_header(receptionist_token))
    assert response.status_code == 409


def test_patient_cannot_manage_billing(client, patient_token, receptionist_token, patient_record, doctor_professional):
    appointment_id = _create_appointment(client, receptionist_token, patient_record, doctor_professional)
    response = client.post(
        "/billing",
        json={"appointment_id": appointment_id, "amount": "150.00", "payment_method": "dinheiro"},
        headers=auth_header(patient_token),
    )
    assert response.status_code == 403
