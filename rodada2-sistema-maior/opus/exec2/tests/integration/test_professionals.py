from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.professional import Professional
from tests.factories import API, make_appointment, make_doctor

DOCTOR = {
    "full_name": "Rafael Mendes",
    "professional_type": "medico",
    "crm": "123456/sp",
    "specialty": "Ortopedia",
    "email": "rafael@clinica.com.br",
    "phone": "(11) 3333-4444",
    "consultation_fee": "250.00",
}
NURSE = {"full_name": "Lúcia Ramos", "professional_type": "enfermeiro", "coren": "COREN-RJ 445566"}


class TestProfessionalCrud:
    def test_admin_creates_doctor_with_normalized_crm(self, client: TestClient, admin_h: dict) -> None:
        response = client.post(f"{API}/professionals", json=DOCTOR, headers=admin_h)
        assert response.status_code == 201, response.text
        assert response.json()["crm"] == "CRM/SP 123456"
        assert response.json()["consultation_fee"] == "250.00"

    def test_admin_creates_nurse(self, client: TestClient, admin_h: dict) -> None:
        response = client.post(f"{API}/professionals", json=NURSE, headers=admin_h)
        assert response.status_code == 201
        assert response.json()["coren"] == "COREN/RJ 445566"

    @pytest.mark.parametrize(
        ("payload", "fragment"),
        [
            ({**DOCTOR, "crm": "CRM/ZZ 123"}, "UF do CRM"),
            ({**DOCTOR, "crm": "12345678/SP"}, "formato inválido"),
            ({**DOCTOR, "crm": None}, "CRM é obrigatório"),
            ({**DOCTOR, "specialty": None}, "Especialidade é obrigatória"),
            ({**NURSE, "crm": "CRM/SP 1234"}, "não possuem CRM"),
            ({**NURSE, "coren": None}, "COREN é obrigatório"),
        ],
    )
    def test_registration_validation(self, client: TestClient, admin_h: dict, payload: dict, fragment: str) -> None:
        response = client.post(f"{API}/professionals", json=payload, headers=admin_h)
        assert response.status_code == 422
        assert fragment in response.json()["error"]["details"][0]["message"]

    def test_duplicate_crm(self, client: TestClient, admin_h: dict) -> None:
        client.post(f"{API}/professionals", json=DOCTOR, headers=admin_h)
        duplicate = client.post(f"{API}/professionals", json={**DOCTOR, "crm": "CRM/SP 123456"}, headers=admin_h)
        assert duplicate.status_code == 409

    def test_only_admin_manages_professionals(self, client: TestClient, reception_h: dict, doctor_h: dict) -> None:
        assert client.post(f"{API}/professionals", json=DOCTOR, headers=reception_h).status_code == 403
        assert client.post(f"{API}/professionals", json=DOCTOR, headers=doctor_h).status_code == 403

    def test_search_by_specialty(
        self, client: TestClient, patient_h: dict, doctor: Professional, doctor2: Professional, nurse: Professional
    ) -> None:
        response = client.get(f"{API}/professionals", params={"specialty": "cardio"}, headers=patient_h)
        assert [p["id"] for p in response.json()["items"]] == [doctor.id]
        nurses = client.get(f"{API}/professionals", params={"professional_type": "enfermeiro"}, headers=patient_h)
        assert [p["id"] for p in nurses.json()["items"]] == [nurse.id]
        specialties = client.get(f"{API}/professionals/specialties", headers=patient_h)
        assert specialties.json() == ["Cardiologia", "Dermatologia"]

    def test_update_professional(self, client: TestClient, admin_h: dict, doctor: Professional) -> None:
        response = client.patch(
            f"{API}/professionals/{doctor.id}", json={"specialty": "Cardiologia Pediátrica"}, headers=admin_h
        )
        assert response.status_code == 200
        assert response.json()["specialty"] == "Cardiologia Pediátrica"
        coren = client.patch(f"{API}/professionals/{doctor.id}", json={"coren": "COREN/SP 1"}, headers=admin_h)
        assert coren.status_code == 422

    def test_cannot_deactivate_with_future_appointments(
        self, client: TestClient, admin_h: dict, doctor: Professional, patient: Patient, db: Session
    ) -> None:
        make_appointment(db, patient, doctor, datetime(2030, 1, 9, 10, 0))
        assert client.delete(f"{API}/professionals/{doctor.id}", headers=admin_h).status_code == 409

    def test_deactivate_professional(self, client: TestClient, admin_h: dict, doctor2: Professional) -> None:
        assert client.delete(f"{API}/professionals/{doctor2.id}", headers=admin_h).status_code == 204
        listed = client.get(f"{API}/professionals", headers=admin_h).json()
        assert doctor2.id not in [p["id"] for p in listed["items"]]


class TestAvailability:
    @pytest.fixture
    def bare_doctor(self, db: Session) -> Professional:
        return make_doctor(db, full_name="Sem Agenda", weekdays=())

    def test_reception_adds_availability(
        self, client: TestClient, reception_h: dict, bare_doctor: Professional
    ) -> None:
        payload = {"weekday": 5, "start_time": "08:00", "end_time": "12:00", "slot_minutes": 20}
        response = client.post(f"{API}/professionals/{bare_doctor.id}/availability", json=payload, headers=reception_h)
        assert response.status_code == 201
        assert response.json()["weekday_name"] == "sábado"
        listed = client.get(f"{API}/professionals/{bare_doctor.id}/availability", headers=reception_h)
        assert len(listed.json()) == 1

    def test_overlapping_windows_are_rejected(self, client: TestClient, admin_h: dict, doctor: Professional) -> None:
        payload = {"weekday": 0, "start_time": "11:00", "end_time": "13:00"}
        response = client.post(f"{API}/professionals/{doctor.id}/availability", json=payload, headers=admin_h)
        assert response.status_code == 409
        assert response.json()["error"]["details"]["conflito_com"]["inicio"] == "08:00"

    @pytest.mark.parametrize(
        "payload",
        [
            {"weekday": 7, "start_time": "08:00", "end_time": "12:00"},
            {"weekday": 1, "start_time": "12:00", "end_time": "08:00"},
            {"weekday": 1, "start_time": "08:00", "end_time": "08:20", "slot_minutes": 30},
            {"weekday": 1, "start_time": "08:00:30", "end_time": "12:00"},
            {"weekday": 1, "start_time": "08:00", "end_time": "12:00", "slot_minutes": 5},
        ],
    )
    def test_invalid_windows(self, client: TestClient, admin_h: dict, doctor: Professional, payload: dict) -> None:
        response = client.post(f"{API}/professionals/{doctor.id}/availability", json=payload, headers=admin_h)
        assert response.status_code == 422

    def test_doctor_manages_only_own_availability(
        self, client: TestClient, doctor: Professional, doctor2: Professional, doctor_h: dict
    ) -> None:
        payload = {"weekday": 5, "start_time": "08:00", "end_time": "10:00"}
        assert (
            client.post(f"{API}/professionals/{doctor.id}/availability", json=payload, headers=doctor_h).status_code
            == 201
        )
        other = client.post(f"{API}/professionals/{doctor2.id}/availability", json=payload, headers=doctor_h)
        assert other.status_code == 403

    def test_patient_cannot_manage_availability(
        self, client: TestClient, doctor: Professional, patient_h: dict
    ) -> None:
        payload = {"weekday": 5, "start_time": "08:00", "end_time": "10:00"}
        assert (
            client.post(f"{API}/professionals/{doctor.id}/availability", json=payload, headers=patient_h).status_code
            == 403
        )

    def test_remove_availability(self, client: TestClient, admin_h: dict, doctor: Professional) -> None:
        availability_id = doctor.availabilities[0].id
        url = f"{API}/professionals/{doctor.id}/availability/{availability_id}"
        assert client.delete(url, headers=admin_h).status_code == 204
        assert client.delete(url, headers=admin_h).status_code == 404

    def test_available_slots_exclude_booked_and_past(
        self, client: TestClient, patient_h: dict, doctor: Professional, patient: Patient, db: Session
    ) -> None:
        make_appointment(db, patient, doctor, datetime(2030, 1, 7, 9, 0))
        response = client.get(
            f"{API}/professionals/{doctor.id}/available-slots", params={"date": "2030-01-07"}, headers=patient_h
        )
        assert response.status_code == 200
        starts = [slot["start_at"][11:16] for slot in response.json()["slots"]]
        assert "08:00" not in starts  # o relógio está em 08:00: horário já começou
        assert "09:00" not in starts  # ocupado
        assert starts[0] == "08:30"
        assert len(starts) == 16 - 2

    def test_available_slots_for_past_date(self, client: TestClient, patient_h: dict, doctor: Professional) -> None:
        response = client.get(
            f"{API}/professionals/{doctor.id}/available-slots", params={"date": "2030-01-06"}, headers=patient_h
        )
        assert response.status_code == 422

    def test_available_slots_for_nurse_is_rejected(
        self, client: TestClient, patient_h: dict, nurse: Professional
    ) -> None:
        response = client.get(
            f"{API}/professionals/{nurse.id}/available-slots", params={"date": "2030-01-08"}, headers=patient_h
        )
        assert response.status_code == 422
