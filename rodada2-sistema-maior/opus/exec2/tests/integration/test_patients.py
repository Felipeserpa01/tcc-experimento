from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.patient import HealthInsurance, Patient
from app.models.professional import Professional
from tests.factories import API, make_appointment, make_insurance, make_patient

PATIENT = {
    "full_name": "Fernanda Costa",
    "cpf": "111.444.777-35",
    "birth_date": "1992-07-15",
    "sex": "feminino",
    "phone": "(21) 99876-5432",
    "email": "Fernanda@Email.com",
    "address": {
        "street": "Rua das Flores",
        "number": "45",
        "complement": "Apto 101",
        "neighborhood": "Centro",
        "city": "Rio de Janeiro",
        "state": "RJ",
        "zip_code": "20040-020",
    },
    "allergies": [{"substance": "Dipirona", "reaction": "Urticária", "severity": "moderada"}],
    "notes": "Paciente hipertensa.",
}


class TestCreatePatient:
    def test_reception_creates_patient_with_normalized_data(
        self, client: TestClient, reception_h: dict, insurance: HealthInsurance
    ) -> None:
        payload = {**PATIENT, "insurance_id": insurance.id, "insurance_card_number": "0001 2345"}
        response = client.post(f"{API}/patients", json=payload, headers=reception_h)
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["cpf"] == "11144477735"
        assert body["phone"] == "21998765432"
        assert body["email"] == "fernanda@email.com"
        assert body["address"]["zip_code"] == "20040020"
        assert body["insurance"]["name"] == "Saúde Total"
        assert body["allergies"][0]["severity"] == "moderada"
        assert body["age"] == 37

    @pytest.mark.parametrize("headers_fixture", ["doctor_h", "nurse_h", "patient_h"])
    def test_only_front_desk_creates_patients(
        self, client: TestClient, request: pytest.FixtureRequest, headers_fixture: str
    ) -> None:
        headers = request.getfixturevalue(headers_fixture)
        assert client.post(f"{API}/patients", json=PATIENT, headers=headers).status_code == 403

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("cpf", "111.444.777-36"),
            ("phone", "1234"),
            ("birth_date", "2031-01-01"),
            ("sex", "x"),
            ("full_name", "A1"),
            ("email", "nao-e-email"),
        ],
    )
    def test_field_validation(self, client: TestClient, reception_h: dict, field: str, value: str) -> None:
        response = client.post(f"{API}/patients", json={**PATIENT, field: value}, headers=reception_h)
        assert response.status_code == 422
        assert response.json()["error"]["details"][0]["field"] == field

    def test_missing_required_fields_are_listed(self, client: TestClient, reception_h: dict) -> None:
        response = client.post(f"{API}/patients", json={"full_name": "Fulano de Tal"}, headers=reception_h)
        assert response.status_code == 422
        fields = {d["field"] for d in response.json()["error"]["details"]}
        assert {"cpf", "birth_date", "sex", "phone"} <= fields
        assert all(d["message"] == "Campo obrigatório." for d in response.json()["error"]["details"])

    def test_duplicate_cpf(self, client: TestClient, reception_h: dict) -> None:
        assert client.post(f"{API}/patients", json=PATIENT, headers=reception_h).status_code == 201
        duplicate = client.post(f"{API}/patients", json={**PATIENT, "cpf": "11144477735"}, headers=reception_h)
        assert duplicate.status_code == 409

    def test_insurance_rules(self, client: TestClient, reception_h: dict, db: Session) -> None:
        missing = client.post(f"{API}/patients", json={**PATIENT, "insurance_id": 999}, headers=reception_h)
        assert missing.status_code == 404
        inactive = make_insurance(db, name="Plano Extinto", active=False)
        response = client.post(f"{API}/patients", json={**PATIENT, "insurance_id": inactive.id}, headers=reception_h)
        assert response.status_code == 422
        card_only = client.post(
            f"{API}/patients", json={**PATIENT, "insurance_card_number": "123"}, headers=reception_h
        )
        assert card_only.status_code == 422

    def test_incomplete_address(self, client: TestClient, reception_h: dict) -> None:
        payload = {**PATIENT, "address": {"street": "Rua A", "city": "Rio de Janeiro"}}
        response = client.post(f"{API}/patients", json=payload, headers=reception_h)
        assert response.status_code == 422
        fields = {d["field"] for d in response.json()["error"]["details"]}
        assert {"address.number", "address.state", "address.zip_code"} <= fields


class TestSearchPatients:
    @pytest.fixture
    def population(self, db: Session, insurance: HealthInsurance) -> list[Patient]:
        other = make_insurance(db, name="Vida Plena", discount="10")
        return [
            make_patient(db, full_name="Ana Beatriz Souza", insurance=insurance),
            make_patient(db, full_name="Bruno Almeida", insurance=other),
            make_patient(db, full_name="Carla Souza", insurance=insurance),
            make_patient(db, full_name="Daniel Rocha"),
        ]

    def test_search_by_name_is_partial_and_case_insensitive(
        self, client: TestClient, reception_h: dict, population: list[Patient]
    ) -> None:
        response = client.get(f"{API}/patients", params={"name": "SOUZA"}, headers=reception_h)
        assert [p["full_name"] for p in response.json()["items"]] == ["Ana Beatriz Souza", "Carla Souza"]

    def test_search_by_cpf_prefix(self, client: TestClient, reception_h: dict, population: list[Patient]) -> None:
        target = population[1]
        formatted = f"{target.cpf[:3]}.{target.cpf[3:6]}"
        response = client.get(f"{API}/patients", params={"cpf": formatted}, headers=reception_h)
        assert [p["id"] for p in response.json()["items"]] == [target.id]
        generic = client.get(f"{API}/patients", params={"q": target.cpf}, headers=reception_h)
        assert generic.json()["total"] == 1

    def test_search_by_insurance(
        self, client: TestClient, reception_h: dict, population: list[Patient], insurance: HealthInsurance
    ) -> None:
        by_id = client.get(f"{API}/patients", params={"insurance_id": insurance.id}, headers=reception_h)
        assert by_id.json()["total"] == 2
        by_name = client.get(f"{API}/patients", params={"insurance_name": "vida"}, headers=reception_h)
        assert [p["full_name"] for p in by_name.json()["items"]] == ["Bruno Almeida"]

    def test_pagination_and_sorting(self, client: TestClient, doctor_h: dict, population: list[Patient]) -> None:
        response = client.get(
            f"{API}/patients",
            params={"page": 2, "page_size": 3, "sort_by": "full_name", "sort_order": "desc"},
            headers=doctor_h,
        )
        body = response.json()
        assert body["total"] == 4 and body["pages"] == 2 and body["page"] == 2
        assert [p["full_name"] for p in body["items"]] == ["Ana Beatriz Souza"]

    def test_like_wildcards_are_escaped(self, client: TestClient, reception_h: dict, population: list[Patient]) -> None:
        response = client.get(f"{API}/patients", params={"name": "%%"}, headers=reception_h)
        assert response.json()["total"] == 0

    def test_invalid_pagination(self, client: TestClient, reception_h: dict) -> None:
        assert client.get(f"{API}/patients", params={"page": 0}, headers=reception_h).status_code == 422
        assert client.get(f"{API}/patients", params={"page_size": 101}, headers=reception_h).status_code == 422


class TestPatientAccessScope:
    def test_patient_reads_only_own_record(
        self, client: TestClient, patient: Patient, other_patient: Patient, patient_h: dict
    ) -> None:
        assert client.get(f"{API}/patients/me", headers=patient_h).json()["id"] == patient.id
        assert client.get(f"{API}/patients/{patient.id}", headers=patient_h).status_code == 200
        forbidden = client.get(f"{API}/patients/{other_patient.id}", headers=patient_h)
        assert forbidden.status_code == 403
        assert client.get(f"{API}/patients", headers=patient_h).status_code == 403

    def test_staff_reads_any_patient(
        self, client: TestClient, patient: Patient, reception_h: dict, doctor_h: dict, nurse_h: dict
    ) -> None:
        for headers in (reception_h, doctor_h, nurse_h):
            assert client.get(f"{API}/patients/{patient.id}", headers=headers).status_code == 200

    def test_me_is_only_for_patients(self, client: TestClient, reception_h: dict) -> None:
        assert client.get(f"{API}/patients/me", headers=reception_h).status_code == 403

    def test_not_found(self, client: TestClient, reception_h: dict) -> None:
        response = client.get(f"{API}/patients/9999", headers=reception_h)
        assert response.status_code == 404
        assert response.json()["error"]["message"] == "Paciente não encontrado."


class TestUpdatePatient:
    def test_reception_updates_any_field(self, client: TestClient, patient: Patient, reception_h: dict) -> None:
        response = client.patch(
            f"{API}/patients/{patient.id}", json={"full_name": "Maria da Silva Santos"}, headers=reception_h
        )
        assert response.status_code == 200
        assert response.json()["full_name"] == "Maria da Silva Santos"

    def test_doctor_updates_only_clinical_fields(self, client: TestClient, patient: Patient, doctor_h: dict) -> None:
        ok = client.patch(
            f"{API}/patients/{patient.id}",
            json={"allergies": [{"substance": "Penicilina", "severity": "grave"}]},
            headers=doctor_h,
        )
        assert ok.status_code == 200
        assert ok.json()["allergies"][0]["substance"] == "Penicilina"

        denied = client.patch(f"{API}/patients/{patient.id}", json={"phone": "11912345678"}, headers=doctor_h)
        assert denied.status_code == 403
        assert denied.json()["error"]["details"]["campos_nao_permitidos"] == ["phone"]

    def test_patient_updates_only_own_contact_data(
        self, client: TestClient, patient: Patient, other_patient: Patient, patient_h: dict
    ) -> None:
        ok = client.patch(f"{API}/patients/{patient.id}", json={"phone": "(11) 91111-2222"}, headers=patient_h)
        assert ok.status_code == 200 and ok.json()["phone"] == "11911112222"
        assert client.patch(f"{API}/patients/{patient.id}", json={"notes": "x"}, headers=patient_h).status_code == 403
        assert (
            client.patch(
                f"{API}/patients/{other_patient.id}", json={"phone": "11911112222"}, headers=patient_h
            ).status_code
            == 403
        )

    def test_required_fields_cannot_be_nulled(self, client: TestClient, patient: Patient, reception_h: dict) -> None:
        response = client.patch(f"{API}/patients/{patient.id}", json={"cpf": None}, headers=reception_h)
        assert response.status_code == 422
        assert response.json()["error"]["details"][0]["message"] == "Este campo não pode ser nulo."

    def test_empty_update_and_unknown_fields(self, client: TestClient, patient: Patient, reception_h: dict) -> None:
        assert client.patch(f"{API}/patients/{patient.id}", json={}, headers=reception_h).status_code == 422
        response = client.patch(f"{API}/patients/{patient.id}", json={"is_admin": True}, headers=reception_h)
        assert response.status_code == 422

    def test_cpf_change_conflict(
        self, client: TestClient, patient: Patient, other_patient: Patient, reception_h: dict
    ) -> None:
        response = client.patch(f"{API}/patients/{patient.id}", json={"cpf": other_patient.cpf}, headers=reception_h)
        assert response.status_code == 409

    def test_removing_insurance_clears_card(
        self, client: TestClient, reception_h: dict, db: Session, insurance: HealthInsurance
    ) -> None:
        created = client.post(
            f"{API}/patients",
            json={**PATIENT, "insurance_id": insurance.id, "insurance_card_number": "ABC123"},
            headers=reception_h,
        ).json()
        response = client.patch(f"{API}/patients/{created['id']}", json={"insurance_id": None}, headers=reception_h)
        assert response.json()["insurance"] is None
        assert response.json()["insurance_card_number"] is None


class TestDeactivatePatient:
    def test_admin_deactivates_patient_and_account(
        self, client: TestClient, patient: Patient, patient_h: dict, admin_h: dict, db: Session
    ) -> None:
        assert client.delete(f"{API}/patients/{patient.id}", headers=admin_h).status_code == 204
        db.expire_all()
        assert patient.is_active is False
        assert patient.user.is_active is False
        assert client.get(f"{API}/patients/me", headers=patient_h).status_code == 401
        listed = client.get(f"{API}/patients", headers=admin_h).json()
        assert patient.id not in [p["id"] for p in listed["items"]]
        inactive = client.get(f"{API}/patients", params={"is_active": False}, headers=admin_h).json()
        assert [p["id"] for p in inactive["items"]] == [patient.id]

    def test_reception_cannot_delete(self, client: TestClient, patient: Patient, reception_h: dict) -> None:
        assert client.delete(f"{API}/patients/{patient.id}", headers=reception_h).status_code == 403

    def test_cannot_deactivate_with_future_appointments(
        self, client: TestClient, patient: Patient, doctor: Professional, admin_h: dict, db: Session
    ) -> None:
        make_appointment(db, patient, doctor, datetime(2030, 1, 8, 9, 0))
        response = client.delete(f"{API}/patients/{patient.id}", headers=admin_h)
        assert response.status_code == 409
        assert response.json()["error"]["details"]["consultas_futuras"] == 1
