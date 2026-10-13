"""Integration tests for professional CRUD, CRM validation and availability scheduling."""
from tests.conftest import VALID_PASSWORD

VALID_DOCTOR_PAYLOAD = {
    "nome": "Dr. Pedro Alves",
    "tipo": "medico",
    "crm": "654321-RJ",
    "especialidade": "Dermatologia",
    "email": "pedro.alves@clinica.com",
    "password": VALID_PASSWORD,
}


def test_admin_can_create_doctor(client, admin_headers):
    resp = client.post("/professionals", json=VALID_DOCTOR_PAYLOAD, headers=admin_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["crm"] == "654321-RJ"
    assert body["tipo"] == "medico"


def test_non_admin_cannot_create_doctor(client, recepcionista_headers):
    resp = client.post("/professionals", json=VALID_DOCTOR_PAYLOAD, headers=recepcionista_headers)
    assert resp.status_code == 403


def test_create_doctor_rejects_invalid_crm(client, admin_headers):
    payload = dict(VALID_DOCTOR_PAYLOAD, crm="12-X", email="outro@clinica.com")
    resp = client.post("/professionals", json=payload, headers=admin_headers)
    assert resp.status_code == 422


def test_create_doctor_requires_especialidade(client, admin_headers):
    payload = dict(VALID_DOCTOR_PAYLOAD, especialidade=None, email="outro2@clinica.com")
    resp = client.post("/professionals", json=payload, headers=admin_headers)
    assert resp.status_code == 422


def test_create_nurse_does_not_require_crm(client, admin_headers):
    payload = {
        "nome": "Enf. Julia Costa",
        "tipo": "enfermeiro",
        "email": "julia.costa@clinica.com",
        "password": VALID_PASSWORD,
    }
    resp = client.post("/professionals", json=payload, headers=admin_headers)
    assert resp.status_code == 201, resp.text
    assert resp.json()["crm"] is None


def test_create_doctor_rejects_duplicate_crm(client, admin_headers):
    client.post("/professionals", json=VALID_DOCTOR_PAYLOAD, headers=admin_headers)
    dup = dict(VALID_DOCTOR_PAYLOAD, email="segundo@clinica.com")
    resp = client.post("/professionals", json=dup, headers=admin_headers)
    assert resp.status_code == 409


def test_search_professionals_by_specialty(client, admin_headers):
    client.post("/professionals", json=VALID_DOCTOR_PAYLOAD, headers=admin_headers)
    resp = client.get("/professionals?especialidade=Dermato", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["especialidade"] == "Dermatologia"


def test_add_availability_slot(client, enfermeiro_user_and_headers):
    professional, headers = enfermeiro_user_and_headers
    payload = {"dia_semana": 0, "hora_inicio": "08:00:00", "hora_fim": "12:00:00"}
    resp = client.post(f"/professionals/{professional.id}/availability", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text


def test_availability_slot_rejects_invalid_time_range(client, enfermeiro_user_and_headers):
    professional, headers = enfermeiro_user_and_headers
    payload = {"dia_semana": 0, "hora_inicio": "12:00:00", "hora_fim": "08:00:00"}
    resp = client.post(f"/professionals/{professional.id}/availability", json=payload, headers=headers)
    assert resp.status_code == 422


def test_availability_slot_rejects_overlap(client, enfermeiro_user_and_headers):
    professional, headers = enfermeiro_user_and_headers
    client.post(
        f"/professionals/{professional.id}/availability",
        json={"dia_semana": 1, "hora_inicio": "08:00:00", "hora_fim": "12:00:00"},
        headers=headers,
    )
    overlap = client.post(
        f"/professionals/{professional.id}/availability",
        json={"dia_semana": 1, "hora_inicio": "10:00:00", "hora_fim": "14:00:00"},
        headers=headers,
    )
    assert overlap.status_code == 422


def test_doctor_cannot_manage_another_doctors_agenda(client, admin_headers, medico_user_and_headers):
    professional, _ = medico_user_and_headers
    created = client.post(
        "/professionals",
        json=dict(VALID_DOCTOR_PAYLOAD, email="outro3@clinica.com"),
        headers=admin_headers,
    )
    assert created.status_code == 201
    # Log in as the *other* doctor and try to modify the first doctor's agenda.
    login = client.post("/auth/login", json={"email": "outro3@clinica.com", "password": VALID_PASSWORD})
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = client.post(
        f"/professionals/{professional.id}/availability",
        json={"dia_semana": 2, "hora_inicio": "08:00:00", "hora_fim": "12:00:00"},
        headers=other_headers,
    )
    assert resp.status_code == 403
