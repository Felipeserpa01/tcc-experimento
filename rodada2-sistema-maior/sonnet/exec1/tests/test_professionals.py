from tests.conftest import auth_header

DOCTOR_PAYLOAD = {
    "full_name": "Dr. Pedro Lima",
    "professional_type": "medico",
    "license_number": "654321-RJ",
    "specialty": "Ortopedia",
    "email": "pedro.lima@clinica.com",
    "password": "Senha123!",
}


def test_admin_creates_professional(client, admin_token):
    response = client.post("/professionals", json=DOCTOR_PAYLOAD, headers=auth_header(admin_token))
    assert response.status_code == 201, response.text
    assert response.json()["license_number"] == "654321-RJ"


def test_non_admin_cannot_create_professional(client, receptionist_token):
    response = client.post(
        "/professionals", json=DOCTOR_PAYLOAD, headers=auth_header(receptionist_token)
    )
    assert response.status_code == 403


def test_create_professional_rejects_invalid_crm(client, admin_token):
    payload = dict(DOCTOR_PAYLOAD, license_number="invalid")
    response = client.post("/professionals", json=payload, headers=auth_header(admin_token))
    assert response.status_code == 422


def test_doctor_requires_specialty(client, admin_token):
    payload = dict(DOCTOR_PAYLOAD, specialty=None)
    response = client.post("/professionals", json=payload, headers=auth_header(admin_token))
    assert response.status_code == 422


def test_search_professionals_by_specialty(client, admin_token):
    client.post("/professionals", json=DOCTOR_PAYLOAD, headers=auth_header(admin_token))
    response = client.get(
        "/professionals", params={"specialty": "Ortopedia"}, headers=auth_header(admin_token)
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_add_and_list_availability(client, admin_token, doctor_professional):
    response = client.post(
        f"/professionals/{doctor_professional.id}/availability",
        json={"weekday": 1, "start_time": "09:00:00", "end_time": "17:00:00"},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 201, response.text

    list_response = client.get(
        f"/professionals/{doctor_professional.id}/availability", headers=auth_header(admin_token)
    )
    assert list_response.status_code == 200
    assert len(list_response.json()) >= 1


def test_add_availability_rejects_invalid_time_range(client, admin_token, doctor_professional):
    response = client.post(
        f"/professionals/{doctor_professional.id}/availability",
        json={"weekday": 1, "start_time": "18:00:00", "end_time": "09:00:00"},
        headers=auth_header(admin_token),
    )
    assert response.status_code == 422
