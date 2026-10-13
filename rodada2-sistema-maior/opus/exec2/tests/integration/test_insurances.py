import pytest
from fastapi.testclient import TestClient

from app.models.patient import HealthInsurance
from tests.factories import API

PLAN = {"name": "Bem Estar Saúde", "ans_code": "123456", "discount_percent": "15.50"}


class TestInsurances:
    def test_admin_creates_insurance(self, client: TestClient, admin_h: dict) -> None:
        response = client.post(f"{API}/insurances", json=PLAN, headers=admin_h)
        assert response.status_code == 201
        assert response.json()["discount_percent"] == "15.50"
        assert response.json()["is_active"] is True

    def test_only_admin_manages(self, client: TestClient, reception_h: dict, patient_h: dict) -> None:
        assert client.post(f"{API}/insurances", json=PLAN, headers=reception_h).status_code == 403
        assert client.post(f"{API}/insurances", json=PLAN, headers=patient_h).status_code == 403

    @pytest.mark.parametrize(
        "payload",
        [
            {**PLAN, "discount_percent": "100.01"},
            {**PLAN, "discount_percent": "-1"},
            {**PLAN, "discount_percent": "10.555"},
            {**PLAN, "ans_code": "12AB56"},
            {**PLAN, "name": "X"},
        ],
    )
    def test_validation(self, client: TestClient, admin_h: dict, payload: dict) -> None:
        assert client.post(f"{API}/insurances", json=payload, headers=admin_h).status_code == 422

    def test_uniqueness(self, client: TestClient, admin_h: dict) -> None:
        client.post(f"{API}/insurances", json=PLAN, headers=admin_h)
        same_name = client.post(
            f"{API}/insurances", json={**PLAN, "name": "BEM ESTAR SAÚDE", "ans_code": None}, headers=admin_h
        )
        assert same_name.status_code == 409
        same_ans = client.post(f"{API}/insurances", json={**PLAN, "name": "Outro Plano"}, headers=admin_h)
        assert same_ans.status_code == 409

    def test_list_get_and_update(
        self, client: TestClient, admin_h: dict, patient_h: dict, insurance: HealthInsurance
    ) -> None:
        listed = client.get(f"{API}/insurances", params={"name": "saúde"}, headers=patient_h)
        assert listed.status_code == 200 and listed.json()["total"] == 1
        assert client.get(f"{API}/insurances/{insurance.id}", headers=patient_h).json()["name"] == "Saúde Total"
        assert client.get(f"{API}/insurances/999", headers=patient_h).status_code == 404

        updated = client.patch(
            f"{API}/insurances/{insurance.id}", json={"discount_percent": "25", "is_active": False}, headers=admin_h
        )
        assert updated.status_code == 200
        assert updated.json()["discount_percent"] == "25.00"
        assert client.get(f"{API}/insurances", headers=patient_h).json()["total"] == 0
        assert client.get(f"{API}/insurances", params={"is_active": False}, headers=patient_h).json()["total"] == 1

    def test_update_validations(self, client: TestClient, admin_h: dict, insurance: HealthInsurance) -> None:
        url = f"{API}/insurances/{insurance.id}"
        assert client.patch(url, json={}, headers=admin_h).status_code == 422
        assert client.patch(url, json={"name": None}, headers=admin_h).status_code == 422
        other = client.post(f"{API}/insurances", json=PLAN, headers=admin_h).json()
        assert client.patch(url, json={"name": other["name"]}, headers=admin_h).status_code == 409
