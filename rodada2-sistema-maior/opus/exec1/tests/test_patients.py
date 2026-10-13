"""Testes de cadastro, busca e controle de acesso de pacientes."""

from __future__ import annotations


from tests.conftest import API, VALID_CPFS, auth_headers, make_patient


def patient_payload(**overrides) -> dict:
    payload = {
        "full_name": "Paulo Ferreira",
        "cpf": VALID_CPFS[2],
        "birth_date": "1985-07-10",
        "gender": "male",
        "phone": "(11) 97777-6666",
        "email": "paulo@paciente.com",
        "address_street": "Av. Brasil",
        "address_number": "1500",
        "address_complement": "Apto 22",
        "address_district": "Jardins",
        "address_city": "Sao Paulo",
        "address_state": "sp",
        "address_zip_code": "01310-100",
        "allergies": "Penicilina",
        "notes": "Paciente hipertenso",
    }
    payload.update(overrides)
    return payload


class TestCreatePatient:
    def test_receptionist_can_create(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.post(f"{API}/patients", json=patient_payload(), headers=headers)
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["cpf"] == VALID_CPFS[2]
        assert body["cpf_formatted"] == "390.533.447-05"
        assert body["address_state"] == "SP"
        assert body["address_zip_code"] == "01310100"
        assert body["age"] > 0

    def test_admin_can_create(self, client, scenario):
        headers = auth_headers(client, "admin@clinica.com")
        response = client.post(f"{API}/patients", json=patient_payload(), headers=headers)
        assert response.status_code == 201

    def test_doctor_cannot_create(self, client, scenario):
        headers = auth_headers(client, "medico@clinica.com")
        response = client.post(f"{API}/patients", json=patient_payload(), headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "permission_denied"

    def test_patient_cannot_create(self, client, scenario):
        headers = auth_headers(client, "paciente@clinica.com")
        response = client.post(f"{API}/patients", json=patient_payload(), headers=headers)
        assert response.status_code == 403

    def test_unauthenticated_is_rejected(self, client, scenario):
        assert client.post(f"{API}/patients", json=patient_payload()).status_code == 401

    def test_rejects_invalid_cpf(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.post(
            f"{API}/patients", json=patient_payload(cpf="123.456.789-00"), headers=headers
        )
        assert response.status_code == 422

    def test_rejects_duplicate_cpf(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.post(
            f"{API}/patients", json=patient_payload(cpf=VALID_CPFS[0]), headers=headers
        )
        assert response.status_code == 409

    def test_rejects_invalid_state(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.post(
            f"{API}/patients", json=patient_payload(address_state="XX"), headers=headers
        )
        assert response.status_code == 422

    def test_rejects_invalid_phone(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.post(
            f"{API}/patients", json=patient_payload(phone="123"), headers=headers
        )
        assert response.status_code == 422

    def test_rejects_future_birth_date(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.post(
            f"{API}/patients", json=patient_payload(birth_date="2999-01-01"), headers=headers
        )
        assert response.status_code == 422

    def test_rejects_unknown_insurance(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.post(
            f"{API}/patients", json=patient_payload(insurance_id=9999), headers=headers
        )
        assert response.status_code == 404

    def test_creates_portal_account(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.post(
            f"{API}/patients",
            json=patient_payload(create_user_account=True, account_password="SenhaForte@123"),
            headers=headers,
        )
        assert response.status_code == 201
        assert response.json()["user_id"] is not None
        assert auth_headers(client, "paulo@paciente.com", "SenhaForte@123")

    def test_portal_account_requires_password(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.post(
            f"{API}/patients", json=patient_payload(create_user_account=True), headers=headers
        )
        assert response.status_code == 422


class TestSearchPatients:
    def test_search_by_name(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.get(f"{API}/patients", params={"query": "Maria"}, headers=headers)
        assert response.status_code == 200
        names = [item["full_name"] for item in response.json()["items"]]
        assert "Maria Silva" in names

    def test_search_by_cpf(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.get(
            f"{API}/patients", params={"cpf": "529.982.247-25"}, headers=headers
        )
        assert response.json()["meta"]["total"] == 1

    def test_search_by_insurance_name(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.get(
            f"{API}/patients", params={"insurance": "Saude Total"}, headers=headers
        )
        assert response.json()["meta"]["total"] == 1

    def test_search_by_insurance_id(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.get(
            f"{API}/patients",
            params={"insurance_id": scenario["insurance"].id},
            headers=headers,
        )
        assert response.json()["meta"]["total"] == 1

    def test_pagination_metadata(self, client, db, scenario):
        for index in range(3, 8):
            make_patient(db, full_name=f"Paciente {index}", cpf=VALID_CPFS[index])
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.get(
            f"{API}/patients", params={"page": 1, "size": 3}, headers=headers
        )
        meta = response.json()["meta"]
        assert meta["total"] == 7
        assert meta["pages"] == 3
        assert meta["has_next"] is True
        assert meta["has_previous"] is False
        assert len(response.json()["items"]) == 3

    def test_second_page(self, client, db, scenario):
        for index in range(3, 8):
            make_patient(db, full_name=f"Paciente {index}", cpf=VALID_CPFS[index])
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.get(
            f"{API}/patients", params={"page": 3, "size": 3}, headers=headers
        )
        meta = response.json()["meta"]
        assert meta["has_next"] is False
        assert meta["has_previous"] is True

    def test_sorting_desc_by_name(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.get(
            f"{API}/patients",
            params={"sort_by": "full_name", "sort_order": "desc"},
            headers=headers,
        )
        names = [item["full_name"] for item in response.json()["items"]]
        assert names == sorted(names, reverse=True)

    def test_invalid_sort_field_returns_400(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.get(
            f"{API}/patients", params={"sort_by": "senha"}, headers=headers
        )
        assert response.status_code == 400
        assert "allowed_sort_fields" in response.json()["error"]["details"]

    def test_page_size_limit_is_enforced(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.get(f"{API}/patients", params={"size": 1000}, headers=headers)
        assert response.status_code == 422


class TestPatientAccessControl:
    def test_patient_sees_only_own_record_in_list(self, client, scenario):
        headers = auth_headers(client, "paciente@clinica.com")
        response = client.get(f"{API}/patients", headers=headers)
        assert response.json()["meta"]["total"] == 1
        assert response.json()["items"][0]["id"] == scenario["patient"].id

    def test_patient_cannot_read_other_patient(self, client, scenario):
        headers = auth_headers(client, "paciente@clinica.com")
        response = client.get(
            f"{API}/patients/{scenario['other_patient'].id}", headers=headers
        )
        assert response.status_code == 403

    def test_patient_can_read_own_record(self, client, scenario):
        headers = auth_headers(client, "paciente@clinica.com")
        response = client.get(f"{API}/patients/{scenario['patient'].id}", headers=headers)
        assert response.status_code == 200

    def test_patients_me_endpoint(self, client, scenario):
        headers = auth_headers(client, "paciente@clinica.com")
        response = client.get(f"{API}/patients/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["id"] == scenario["patient"].id

    def test_doctor_can_read_any_patient(self, client, scenario):
        headers = auth_headers(client, "medico@clinica.com")
        response = client.get(f"{API}/patients/{scenario['patient'].id}", headers=headers)
        assert response.status_code == 200

    def test_nurse_can_read_any_patient(self, client, scenario):
        headers = auth_headers(client, "enfermeiro@clinica.com")
        response = client.get(f"{API}/patients/{scenario['patient'].id}", headers=headers)
        assert response.status_code == 200


class TestUpdatePatient:
    def test_receptionist_updates_any_field(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.patch(
            f"{API}/patients/{scenario['patient'].id}",
            json={"allergies": "Nenhuma conhecida", "notes": "Revisado"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["allergies"] == "Nenhuma conhecida"

    def test_patient_updates_own_contact_data(self, client, scenario):
        headers = auth_headers(client, "paciente@clinica.com")
        response = client.patch(
            f"{API}/patients/{scenario['patient'].id}",
            json={"phone": "11955554444"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["phone"] == "11955554444"

    def test_patient_cannot_change_clinical_fields(self, client, scenario):
        headers = auth_headers(client, "paciente@clinica.com")
        response = client.patch(
            f"{API}/patients/{scenario['patient'].id}",
            json={"allergies": "Nenhuma"},
            headers=headers,
        )
        assert response.status_code == 403
        assert "allergies" in response.json()["error"]["details"]["forbidden_fields"]

    def test_patient_cannot_update_other_patient(self, client, scenario):
        headers = auth_headers(client, "paciente@clinica.com")
        response = client.patch(
            f"{API}/patients/{scenario['other_patient'].id}",
            json={"phone": "11955554444"},
            headers=headers,
        )
        assert response.status_code == 403

    def test_update_validates_phone(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.patch(
            f"{API}/patients/{scenario['patient'].id}",
            json={"phone": "999"},
            headers=headers,
        )
        assert response.status_code == 422

    def test_update_unknown_patient_returns_404(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.patch(
            f"{API}/patients/9999", json={"phone": "11955554444"}, headers=headers
        )
        assert response.status_code == 404


class TestDeletePatient:
    def test_admin_soft_deletes(self, client, scenario):
        headers = auth_headers(client, "admin@clinica.com")
        response = client.delete(f"{API}/patients/{scenario['patient'].id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    def test_receptionist_cannot_delete(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.delete(f"{API}/patients/{scenario['patient'].id}", headers=headers)
        assert response.status_code == 403

    def test_cannot_delete_twice(self, client, scenario):
        headers = auth_headers(client, "admin@clinica.com")
        client.delete(f"{API}/patients/{scenario['patient'].id}", headers=headers)
        response = client.delete(f"{API}/patients/{scenario['patient'].id}", headers=headers)
        assert response.status_code == 422


class TestInsurances:
    def test_create_and_list(self, client, scenario):
        headers = auth_headers(client, "admin@clinica.com")
        response = client.post(
            f"{API}/insurances",
            json={"name": "Vida Plena", "discount_percent": "15.5"},
            headers=headers,
        )
        assert response.status_code == 201
        listing = client.get(f"{API}/insurances", headers=headers).json()
        assert listing["meta"]["total"] == 2

    def test_rejects_duplicate_name(self, client, scenario):
        headers = auth_headers(client, "admin@clinica.com")
        response = client.post(
            f"{API}/insurances", json={"name": "Saude Total"}, headers=headers
        )
        assert response.status_code == 409

    def test_rejects_discount_above_100(self, client, scenario):
        headers = auth_headers(client, "admin@clinica.com")
        response = client.post(
            f"{API}/insurances",
            json={"name": "Convenio Absurdo", "discount_percent": "150"},
            headers=headers,
        )
        assert response.status_code == 422

    def test_doctor_cannot_create_insurance(self, client, scenario):
        headers = auth_headers(client, "medico@clinica.com")
        response = client.post(
            f"{API}/insurances", json={"name": "Outro Convenio"}, headers=headers
        )
        assert response.status_code == 403
