"""Testes de profissionais, validacao de CRM e agenda de disponibilidade."""

from __future__ import annotations

from datetime import timedelta

from tests.conftest import API, auth_headers, next_weekday_at


def doctor_payload(**overrides) -> dict:
    payload = {
        "full_name": "Helena Martins",
        "professional_type": "doctor",
        "council_number": "998877",
        "council_state": "RJ",
        "specialty": "Pediatria",
        "phone": "21999998888",
        "email": "helena@clinica.com",
        "appointment_price": "250.00",
        "appointment_duration_minutes": 30,
    }
    payload.update(overrides)
    return payload


class TestCreateProfessional:
    def test_admin_creates_doctor(self, client, scenario):
        headers = auth_headers(client, "admin@clinica.com")
        response = client.post(f"{API}/professionals", json=doctor_payload(), headers=headers)
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["council_type"] == "CRM"
        assert body["council_label"] == "CRM/RJ 998877"

    def test_nurse_gets_coren(self, client, scenario):
        headers = auth_headers(client, "admin@clinica.com")
        response = client.post(
            f"{API}/professionals",
            json=doctor_payload(
                professional_type="nurse", specialty=None, council_number="445566"
            ),
            headers=headers,
        )
        assert response.status_code == 201
        assert response.json()["council_type"] == "COREN"

    def test_doctor_requires_specialty(self, client, scenario):
        headers = auth_headers(client, "admin@clinica.com")
        response = client.post(
            f"{API}/professionals", json=doctor_payload(specialty=None), headers=headers
        )
        assert response.status_code == 422

    def test_rejects_invalid_council_number(self, client, scenario):
        headers = auth_headers(client, "admin@clinica.com")
        response = client.post(
            f"{API}/professionals", json=doctor_payload(council_number="12"), headers=headers
        )
        assert response.status_code == 422

    def test_rejects_invalid_state(self, client, scenario):
        headers = auth_headers(client, "admin@clinica.com")
        response = client.post(
            f"{API}/professionals", json=doctor_payload(council_state="ZZ"), headers=headers
        )
        assert response.status_code == 422

    def test_rejects_duplicate_council(self, client, scenario):
        headers = auth_headers(client, "admin@clinica.com")
        response = client.post(
            f"{API}/professionals",
            json=doctor_payload(council_number="123456", council_state="SP"),
            headers=headers,
        )
        assert response.status_code == 409

    def test_receptionist_cannot_create(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.post(f"{API}/professionals", json=doctor_payload(), headers=headers)
        assert response.status_code == 403

    def test_creates_login_account(self, client, scenario):
        headers = auth_headers(client, "admin@clinica.com")
        response = client.post(
            f"{API}/professionals",
            json=doctor_payload(
                create_user_account=True,
                account_email="helena@clinica.com",
                account_password="SenhaForte@123",
            ),
            headers=headers,
        )
        assert response.status_code == 201
        assert response.json()["user_id"] is not None
        assert auth_headers(client, "helena@clinica.com", "SenhaForte@123")

    def test_creates_with_inline_schedules(self, client, scenario):
        headers = auth_headers(client, "admin@clinica.com")
        response = client.post(
            f"{API}/professionals",
            json=doctor_payload(
                schedules=[
                    {"weekday": 1, "start_time": "08:00:00", "end_time": "12:00:00"},
                    {"weekday": 1, "start_time": "14:00:00", "end_time": "18:00:00"},
                ]
            ),
            headers=headers,
        )
        assert response.status_code == 201
        assert len(response.json()["schedules"]) == 2


class TestSearchProfessionals:
    def test_search_by_specialty(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.get(
            f"{API}/professionals", params={"specialty": "cardio"}, headers=headers
        )
        assert response.json()["meta"]["total"] == 1
        assert response.json()["items"][0]["specialty"] == "Cardiologia"

    def test_filter_by_type(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.get(
            f"{API}/professionals", params={"professional_type": "nurse"}, headers=headers
        )
        assert response.json()["meta"]["total"] == 1

    def test_search_by_name(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.get(
            f"{API}/professionals", params={"query": "Bruno"}, headers=headers
        )
        assert response.json()["meta"]["total"] == 1

    def test_lists_specialties(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.get(f"{API}/professionals/specialties", headers=headers)
        assert set(response.json()) == {"Cardiologia", "Dermatologia"}

    def test_professional_me(self, client, scenario):
        headers = auth_headers(client, "medico@clinica.com")
        response = client.get(f"{API}/professionals/me", headers=headers)
        assert response.json()["id"] == scenario["doctor"].id

    def test_patient_without_profile_gets_404(self, client, scenario):
        headers = auth_headers(client, "paciente@clinica.com")
        response = client.get(f"{API}/professionals/me", headers=headers)
        assert response.status_code == 404


class TestUpdateProfessional:
    def test_admin_updates_price(self, client, scenario):
        headers = auth_headers(client, "admin@clinica.com")
        response = client.patch(
            f"{API}/professionals/{scenario['doctor'].id}",
            json={"appointment_price": "420.00"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["appointment_price"] == "420.00"

    def test_doctor_updates_own_specialty(self, client, scenario):
        headers = auth_headers(client, "medico@clinica.com")
        response = client.patch(
            f"{API}/professionals/{scenario['doctor'].id}",
            json={"specialty": "Cardiologia Clinica"},
            headers=headers,
        )
        assert response.status_code == 200

    def test_doctor_cannot_change_own_price(self, client, scenario):
        headers = auth_headers(client, "medico@clinica.com")
        response = client.patch(
            f"{API}/professionals/{scenario['doctor'].id}",
            json={"appointment_price": "1000.00"},
            headers=headers,
        )
        assert response.status_code == 403

    def test_doctor_cannot_update_colleague(self, client, scenario):
        headers = auth_headers(client, "medico@clinica.com")
        response = client.patch(
            f"{API}/professionals/{scenario['other_doctor'].id}",
            json={"specialty": "Outra"},
            headers=headers,
        )
        assert response.status_code == 403

    def test_deactivate_requires_admin(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.delete(
            f"{API}/professionals/{scenario['doctor'].id}", headers=headers
        )
        assert response.status_code == 403

    def test_admin_deactivates(self, client, scenario):
        headers = auth_headers(client, "admin@clinica.com")
        response = client.delete(
            f"{API}/professionals/{scenario['other_doctor'].id}", headers=headers
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False


class TestSchedules:
    def test_doctor_creates_own_schedule(self, client, scenario):
        headers = auth_headers(client, "medico@clinica.com")
        response = client.post(
            f"{API}/professionals/{scenario['doctor'].id}/schedules",
            json={"weekday": 5, "start_time": "09:00:00", "end_time": "13:00:00"},
            headers=headers,
        )
        assert response.status_code == 201
        assert response.json()["weekday_name"] == "sabado"

    def test_rejects_overlapping_schedule(self, client, scenario):
        headers = auth_headers(client, "admin@clinica.com")
        response = client.post(
            f"{API}/professionals/{scenario['doctor'].id}/schedules",
            json={"weekday": 0, "start_time": "10:00:00", "end_time": "12:00:00"},
            headers=headers,
        )
        assert response.status_code == 409

    def test_rejects_end_before_start(self, client, scenario):
        headers = auth_headers(client, "admin@clinica.com")
        response = client.post(
            f"{API}/professionals/{scenario['doctor'].id}/schedules",
            json={"weekday": 5, "start_time": "13:00:00", "end_time": "09:00:00"},
            headers=headers,
        )
        assert response.status_code == 422

    def test_rejects_window_shorter_than_slot(self, client, scenario):
        headers = auth_headers(client, "admin@clinica.com")
        response = client.post(
            f"{API}/professionals/{scenario['doctor'].id}/schedules",
            json={
                "weekday": 5,
                "start_time": "09:00:00",
                "end_time": "09:10:00",
                "slot_duration_minutes": 30,
            },
            headers=headers,
        )
        assert response.status_code == 422

    def test_doctor_cannot_manage_colleague_schedule(self, client, scenario):
        headers = auth_headers(client, "medico@clinica.com")
        response = client.post(
            f"{API}/professionals/{scenario['other_doctor'].id}/schedules",
            json={"weekday": 5, "start_time": "09:00:00", "end_time": "13:00:00"},
            headers=headers,
        )
        assert response.status_code == 403

    def test_list_schedules(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.get(
            f"{API}/professionals/{scenario['doctor'].id}/schedules", headers=headers
        )
        assert len(response.json()) == 5

    def test_update_schedule(self, client, db, scenario):
        headers = auth_headers(client, "admin@clinica.com")
        schedule_id = client.get(
            f"{API}/professionals/{scenario['doctor'].id}/schedules", headers=headers
        ).json()[0]["id"]
        response = client.patch(
            f"{API}/professionals/{scenario['doctor'].id}/schedules/{schedule_id}",
            json={"is_active": False},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    def test_delete_schedule(self, client, scenario):
        headers = auth_headers(client, "admin@clinica.com")
        schedule_id = client.get(
            f"{API}/professionals/{scenario['doctor'].id}/schedules", headers=headers
        ).json()[0]["id"]
        response = client.delete(
            f"{API}/professionals/{scenario['doctor'].id}/schedules/{schedule_id}",
            headers=headers,
        )
        assert response.status_code == 204
        remaining = client.get(
            f"{API}/professionals/{scenario['doctor'].id}/schedules", headers=headers
        ).json()
        assert len(remaining) == 4

    def test_schedule_from_other_professional_returns_404(self, client, scenario):
        headers = auth_headers(client, "admin@clinica.com")
        schedule_id = client.get(
            f"{API}/professionals/{scenario['doctor'].id}/schedules", headers=headers
        ).json()[0]["id"]
        response = client.patch(
            f"{API}/professionals/{scenario['other_doctor'].id}/schedules/{schedule_id}",
            json={"is_active": False},
            headers=headers,
        )
        assert response.status_code == 404


class TestAvailability:
    def test_generates_slots_for_workday(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        target = next_weekday_at(9)
        response = client.get(
            f"{API}/professionals/{scenario['doctor'].id}/available-slots",
            params={"date": target.date().isoformat()},
            headers=headers,
        )
        assert response.status_code == 200
        slots = response.json()["slots"]
        assert len(slots) == 20  # 08:00-18:00 em blocos de 30 minutos
        assert all(slot["available"] for slot in slots)

    def test_no_slots_on_weekend(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        target = next_weekday_at(9) + timedelta(days=5)  # sabado
        response = client.get(
            f"{API}/professionals/{scenario['doctor'].id}/available-slots",
            params={"date": target.date().isoformat()},
            headers=headers,
        )
        assert response.json()["slots"] == []

    def test_booked_slot_is_marked_unavailable(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        start = next_weekday_at(9)
        client.post(
            f"{API}/appointments",
            json={
                "patient_id": scenario["patient"].id,
                "professional_id": scenario["doctor"].id,
                "scheduled_start": start.isoformat(),
            },
            headers=headers,
        )
        response = client.get(
            f"{API}/professionals/{scenario['doctor'].id}/available-slots",
            params={"date": start.date().isoformat()},
            headers=headers,
        )
        busy = [slot for slot in response.json()["slots"] if not slot["available"]]
        assert len(busy) == 1
        assert busy[0]["start"].endswith("09:00:00")
