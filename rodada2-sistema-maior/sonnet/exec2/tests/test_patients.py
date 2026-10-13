"""Integration tests for patient CRUD, CPF validation, search and access control."""
VALID_PATIENT_PAYLOAD = {
    "nome": "Maria Oliveira",
    "cpf": "111.444.777-35",
    "data_nascimento": "1985-05-20",
    "sexo": "Feminino",
    "telefone": "11988887777",
    "email": "maria.oliveira@example.com",
    "endereco_rua": "Av. Paulista",
    "endereco_numero": "1000",
    "endereco_bairro": "Bela Vista",
    "endereco_cidade": "São Paulo",
    "endereco_estado": "sp",
    "endereco_cep": "01310-100",
    "convenio": "Bradesco Saúde",
}


def test_create_patient_as_recepcionista_succeeds(client, recepcionista_headers):
    resp = client.post("/patients", json=VALID_PATIENT_PAYLOAD, headers=recepcionista_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["cpf"] == "11144477735"
    assert body["endereco_estado"] == "SP"


def test_create_patient_rejects_invalid_cpf(client, recepcionista_headers):
    payload = dict(VALID_PATIENT_PAYLOAD, cpf="111.111.111-11")
    resp = client.post("/patients", json=payload, headers=recepcionista_headers)
    assert resp.status_code == 422


def test_create_patient_rejects_duplicate_cpf(client, recepcionista_headers):
    client.post("/patients", json=VALID_PATIENT_PAYLOAD, headers=recepcionista_headers)
    dup = dict(VALID_PATIENT_PAYLOAD, email="outro@example.com")
    resp = client.post("/patients", json=dup, headers=recepcionista_headers)
    assert resp.status_code == 409


def test_create_patient_rejects_future_birthdate(client, recepcionista_headers):
    payload = dict(VALID_PATIENT_PAYLOAD, data_nascimento="2999-01-01")
    resp = client.post("/patients", json=payload, headers=recepcionista_headers)
    assert resp.status_code == 422


def test_patient_role_cannot_create_patient(client, patient_user_and_headers):
    _, headers = patient_user_and_headers
    resp = client.post("/patients", json=VALID_PATIENT_PAYLOAD, headers=headers)
    assert resp.status_code == 403


def test_patient_cannot_list_other_patients(client, patient_user_and_headers):
    _, headers = patient_user_and_headers
    resp = client.get("/patients", headers=headers)
    assert resp.status_code == 403


def test_staff_can_list_patients_with_pagination(client, recepcionista_headers):
    for i in range(3):
        payload = dict(VALID_PATIENT_PAYLOAD, email=f"p{i}@example.com")
        payload["cpf"] = ["111.444.777-35", "529.982.247-25", "123.456.789-09"][i]
        client.post("/patients", json=payload, headers=recepcionista_headers)

    resp = client.get("/patients?page=1&page_size=2", headers=recepcionista_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["total_pages"] == 2


def test_patient_can_view_own_record(client, patient_user_and_headers):
    patient, headers = patient_user_and_headers
    resp = client.get(f"/patients/{patient.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == patient.id


def test_patient_cannot_view_other_patient_record(
    client, patient_user_and_headers, recepcionista_headers
):
    _, patient_headers = patient_user_and_headers
    other = client.post("/patients", json=VALID_PATIENT_PAYLOAD, headers=recepcionista_headers)
    other_id = other.json()["id"]

    resp = client.get(f"/patients/{other_id}", headers=patient_headers)
    assert resp.status_code == 403


def test_get_nonexistent_patient_returns_404(client, recepcionista_headers):
    resp = client.get("/patients/9999", headers=recepcionista_headers)
    assert resp.status_code == 404


def test_patient_can_update_own_contact_info(client, patient_user_and_headers):
    patient, headers = patient_user_and_headers
    resp = client.put(
        f"/patients/{patient.id}", json={"telefone": "11900001111"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["telefone"] == "11900001111"


def test_only_admin_can_delete_patient(client, recepcionista_headers, admin_headers):
    created = client.post("/patients", json=VALID_PATIENT_PAYLOAD, headers=recepcionista_headers)
    patient_id = created.json()["id"]

    forbidden = client.delete(f"/patients/{patient_id}", headers=recepcionista_headers)
    assert forbidden.status_code == 403

    allowed = client.delete(f"/patients/{patient_id}", headers=admin_headers)
    assert allowed.status_code == 204
