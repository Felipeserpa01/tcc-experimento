from tests.conftest import auth_header

PATIENT_PAYLOAD = {
    "full_name": "Carlos Pereira",
    "cpf": "390.533.447-05",
    "birth_date": "1988-03-15",
    "sex": "M",
    "phone": "11977776666",
    "address_street": "Av. Central",
    "address_number": "200",
    "address_neighborhood": "Vila Nova",
    "address_city": "São Paulo",
    "address_state": "sp",
    "address_zip_code": "02000-000",
    "insurance": "Unimed",
}


def test_receptionist_creates_patient(client, receptionist_token):
    response = client.post(
        "/patients", json=PATIENT_PAYLOAD, headers=auth_header(receptionist_token)
    )
    assert response.status_code == 201, response.text
    assert response.json()["address_state"] == "SP"


def test_patient_role_cannot_create_patient_record(client, patient_token):
    response = client.post("/patients", json=PATIENT_PAYLOAD, headers=auth_header(patient_token))
    assert response.status_code == 403


def test_create_patient_rejects_duplicate_cpf(client, receptionist_token):
    client.post("/patients", json=PATIENT_PAYLOAD, headers=auth_header(receptionist_token))
    response = client.post(
        "/patients", json=PATIENT_PAYLOAD, headers=auth_header(receptionist_token)
    )
    assert response.status_code == 409


def test_create_patient_rejects_invalid_cpf(client, receptionist_token):
    payload = dict(PATIENT_PAYLOAD, cpf="000.000.000-00")
    response = client.post("/patients", json=payload, headers=auth_header(receptionist_token))
    assert response.status_code == 422


def test_search_patients_by_name(client, receptionist_token):
    client.post("/patients", json=PATIENT_PAYLOAD, headers=auth_header(receptionist_token))
    response = client.get(
        "/patients", params={"name": "Carlos"}, headers=auth_header(receptionist_token)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["full_name"] == "Carlos Pereira"


def test_patient_can_access_own_data(client, patient_token, patient_record):
    response = client.get(f"/patients/{patient_record.id}", headers=auth_header(patient_token))
    assert response.status_code == 200
    assert response.json()["id"] == patient_record.id


def test_patient_cannot_access_other_patient_data(client, patient_token, receptionist_token):
    other_response = client.post(
        "/patients", json=PATIENT_PAYLOAD, headers=auth_header(receptionist_token)
    )
    other_patient_id = other_response.json()["id"]

    response = client.get(f"/patients/{other_patient_id}", headers=auth_header(patient_token))
    assert response.status_code == 403


def test_staff_can_access_any_patient(client, receptionist_token, doctor_token):
    create_response = client.post(
        "/patients", json=PATIENT_PAYLOAD, headers=auth_header(receptionist_token)
    )
    patient_id = create_response.json()["id"]

    response = client.get(f"/patients/{patient_id}", headers=auth_header(doctor_token))
    assert response.status_code == 200


def test_get_own_profile_endpoint(client, patient_token, patient_record):
    response = client.get("/patients/me", headers=auth_header(patient_token))
    assert response.status_code == 200
    assert response.json()["cpf"] == patient_record.cpf
