from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import AppointmentStatus
from app.models.patient import Patient
from app.models.professional import Professional
from tests.conftest import FrozenClock
from tests.factories import API, make_appointment

TUESDAY_9 = "2030-01-08T09:00:00"


def book(client: TestClient, headers: dict, professional_id: int, start: str, patient_id: int | None = None):
    payload: dict = {"professional_id": professional_id, "start_at": start, "reason": "Check-up anual"}
    if patient_id is not None:
        payload["patient_id"] = patient_id
    return client.post(f"{API}/appointments", json=payload, headers=headers)


class TestScheduling:
    def test_reception_schedules_appointment(
        self, client: TestClient, reception_h: dict, patient: Patient, doctor: Professional
    ) -> None:
        response = book(client, reception_h, doctor.id, TUESDAY_9, patient.id)
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["status"] == "agendada"
        assert body["end_at"] == "2030-01-08T09:30:00"
        assert body["professional_name"] == "Carlos Andrade"
        assert body["specialty"] == "Cardiologia"

    def test_patient_schedules_for_self(
        self, client: TestClient, patient_h: dict, patient: Patient, doctor: Professional
    ) -> None:
        response = book(client, patient_h, doctor.id, TUESDAY_9)
        assert response.status_code == 201
        assert response.json()["patient_id"] == patient.id

    def test_patient_cannot_schedule_for_someone_else(
        self, client: TestClient, patient_h: dict, other_patient: Patient, doctor: Professional
    ) -> None:
        assert book(client, patient_h, doctor.id, TUESDAY_9, other_patient.id).status_code == 403

    def test_staff_must_inform_patient(self, client: TestClient, reception_h: dict, doctor: Professional) -> None:
        assert book(client, reception_h, doctor.id, TUESDAY_9).status_code == 422

    def test_nurse_cannot_schedule(
        self, client: TestClient, nurse_h: dict, patient: Patient, doctor: Professional
    ) -> None:
        assert book(client, nurse_h, doctor.id, TUESDAY_9, patient.id).status_code == 403

    def test_doctor_conflict_offers_waitlist(
        self, client: TestClient, reception_h: dict, patient: Patient, other_patient: Patient, doctor: Professional
    ) -> None:
        assert book(client, reception_h, doctor.id, TUESDAY_9, patient.id).status_code == 201
        conflict = book(client, reception_h, doctor.id, TUESDAY_9, other_patient.id)
        assert conflict.status_code == 409
        error = conflict.json()["error"]
        assert error["code"] == "horario_ocupado"
        assert error["details"]["lista_de_espera_disponivel"] is True

    def test_patient_cannot_have_two_appointments_at_same_time(
        self, client: TestClient, reception_h: dict, patient: Patient, doctor: Professional, doctor2: Professional
    ) -> None:
        assert book(client, reception_h, doctor.id, TUESDAY_9, patient.id).status_code == 201
        response = book(client, reception_h, doctor2.id, TUESDAY_9, patient.id)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "conflito_paciente"

    @pytest.mark.parametrize(
        ("start", "code"),
        [
            ("2030-01-12T09:00:00", "fora_da_agenda"),  # sábado
            ("2030-01-08T12:30:00", "fora_da_agenda"),  # almoço
            ("2030-01-08T18:00:00", "fora_da_agenda"),  # após expediente
            ("2030-01-08T09:15:00", "horario_desalinhado"),
            ("2030-01-07T07:30:00", "horario_passado"),
            ("2030-01-06T09:00:00", "horario_passado"),
        ],
    )
    def test_schedule_rules(
        self, client: TestClient, reception_h: dict, patient: Patient, doctor: Professional, start: str, code: str
    ) -> None:
        response = book(client, reception_h, doctor.id, start, patient.id)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == code

    def test_slot_that_already_started_today_is_past(
        self, client: TestClient, reception_h: dict, patient: Patient, doctor: Professional, frozen_clock: FrozenClock
    ) -> None:
        frozen_clock.set(datetime(2030, 1, 7, 9, 10))
        assert book(client, reception_h, doctor.id, "2030-01-07T09:00:00", patient.id).status_code == 422
        assert book(client, reception_h, doctor.id, "2030-01-07T09:30:00", patient.id).status_code == 201

    def test_too_far_in_the_future(
        self, client: TestClient, reception_h: dict, patient: Patient, doctor: Professional
    ) -> None:
        assert book(client, reception_h, doctor.id, "2031-02-04T09:00:00", patient.id).status_code == 422

    def test_timezone_aware_input_is_converted_to_clinic_time(
        self, client: TestClient, reception_h: dict, patient: Patient, doctor: Professional
    ) -> None:
        response = book(client, reception_h, doctor.id, "2030-01-08T12:00:00Z", patient.id)
        assert response.status_code == 201
        assert response.json()["start_at"] == "2030-01-08T09:00:00"

    def test_seconds_are_rejected(
        self, client: TestClient, reception_h: dict, patient: Patient, doctor: Professional
    ) -> None:
        response = book(client, reception_h, doctor.id, "2030-01-08T09:00:30", patient.id)
        assert response.status_code == 422
        assert "sem segundos" in response.json()["error"]["details"][0]["message"]

    def test_only_active_doctors_can_be_booked(
        self,
        client: TestClient,
        reception_h: dict,
        patient: Patient,
        nurse: Professional,
        doctor: Professional,
        db: Session,
    ) -> None:
        assert book(client, reception_h, nurse.id, TUESDAY_9, patient.id).status_code == 422
        doctor.is_active = False
        db.commit()
        assert book(client, reception_h, doctor.id, TUESDAY_9, patient.id).status_code == 422
        assert book(client, reception_h, 9999, TUESDAY_9, patient.id).status_code == 404

    def test_inactive_patient_cannot_be_booked(
        self, client: TestClient, reception_h: dict, patient: Patient, doctor: Professional, db: Session
    ) -> None:
        patient.is_active = False
        db.commit()
        assert book(client, reception_h, doctor.id, TUESDAY_9, patient.id).status_code == 422


class TestLifecycle:
    @pytest.fixture
    def appointment_id(self, client: TestClient, reception_h: dict, patient: Patient, doctor: Professional) -> int:
        return book(client, reception_h, doctor.id, "2030-01-07T10:00:00", patient.id).json()["id"]

    def test_confirm(self, client: TestClient, patient_h: dict, appointment_id: int) -> None:
        response = client.post(f"{API}/appointments/{appointment_id}/confirm", headers=patient_h)
        assert response.status_code == 200
        assert response.json()["status"] == "confirmada"
        again = client.post(f"{API}/appointments/{appointment_id}/confirm", headers=patient_h)
        assert again.status_code == 422
        assert again.json()["error"]["code"] == "transicao_de_status_invalida"

    def test_other_patient_cannot_touch_appointment(
        self, client: TestClient, other_patient_h: dict, appointment_id: int
    ) -> None:
        assert client.get(f"{API}/appointments/{appointment_id}", headers=other_patient_h).status_code == 403
        assert client.post(f"{API}/appointments/{appointment_id}/confirm", headers=other_patient_h).status_code == 403

    def test_cancel_requires_reason_and_frees_slot(
        self, client: TestClient, reception_h: dict, appointment_id: int, other_patient: Patient, doctor: Professional
    ) -> None:
        url = f"{API}/appointments/{appointment_id}/cancel"
        assert client.post(url, json={}, headers=reception_h).status_code == 422
        assert client.post(url, json={"reason": "ok"}, headers=reception_h).status_code == 422
        response = client.post(url, json={"reason": "Paciente viajou"}, headers=reception_h)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "cancelada"
        assert body["cancellation_reason"] == "Paciente viajou"
        assert client.post(url, json={"reason": "De novo"}, headers=reception_h).status_code == 422
        assert book(client, reception_h, doctor.id, "2030-01-07T10:00:00", other_patient.id).status_code == 201

    def test_cannot_cancel_past_appointment(
        self, client: TestClient, reception_h: dict, appointment_id: int, frozen_clock: FrozenClock
    ) -> None:
        frozen_clock.set(datetime(2030, 1, 7, 10, 5))
        response = client.post(
            f"{API}/appointments/{appointment_id}/cancel", json={"reason": "Tarde demais"}, headers=reception_h
        )
        assert response.status_code == 422

    def test_reschedule(self, client: TestClient, patient_h: dict, appointment_id: int) -> None:
        client.post(f"{API}/appointments/{appointment_id}/confirm", headers=patient_h)
        response = client.post(
            f"{API}/appointments/{appointment_id}/reschedule",
            json={"start_at": "2030-01-09T15:00:00"},
            headers=patient_h,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["start_at"] == "2030-01-09T15:00:00"
        assert body["status"] == "agendada"
        assert body["reschedule_count"] == 1

    def test_reschedule_validations(
        self, client: TestClient, reception_h: dict, appointment_id: int, other_patient: Patient, doctor: Professional
    ) -> None:
        book(client, reception_h, doctor.id, TUESDAY_9, other_patient.id)
        url = f"{API}/appointments/{appointment_id}/reschedule"
        assert client.post(url, json={"start_at": TUESDAY_9}, headers=reception_h).status_code == 409
        assert client.post(url, json={"start_at": "2030-01-07T10:00:00"}, headers=reception_h).status_code == 422
        assert client.post(url, json={"start_at": "2030-01-05T10:00:00"}, headers=reception_h).status_code == 422
        client.post(f"{API}/appointments/{appointment_id}/cancel", json={"reason": "Desistiu"}, headers=reception_h)
        assert client.post(url, json={"start_at": "2030-01-09T09:00:00"}, headers=reception_h).status_code == 422

    def test_full_attendance_flow(
        self, client: TestClient, doctor_h: dict, appointment_id: int, frozen_clock: FrozenClock
    ) -> None:
        frozen_clock.set(datetime(2030, 1, 7, 10, 0))
        started = client.post(f"{API}/appointments/{appointment_id}/start", headers=doctor_h)
        assert started.status_code == 200 and started.json()["status"] == "em_andamento"
        completed = client.post(f"{API}/appointments/{appointment_id}/complete", headers=doctor_h)
        assert completed.status_code == 200 and completed.json()["status"] == "realizada"
        assert completed.json()["completed_at"] == "2030-01-07T10:00:00"

    def test_only_responsible_doctor_attends(
        self, client: TestClient, doctor2_h: dict, reception_h: dict, appointment_id: int
    ) -> None:
        assert client.post(f"{API}/appointments/{appointment_id}/start", headers=doctor2_h).status_code == 403
        assert client.post(f"{API}/appointments/{appointment_id}/start", headers=reception_h).status_code == 403

    def test_cannot_start_on_another_day(
        self, client: TestClient, doctor_h: dict, reception_h: dict, patient: Patient, doctor: Professional
    ) -> None:
        tomorrow = book(client, reception_h, doctor.id, TUESDAY_9, patient.id).json()["id"]
        assert client.post(f"{API}/appointments/{tomorrow}/start", headers=doctor_h).status_code == 422

    def test_cannot_complete_without_starting(self, client: TestClient, doctor_h: dict, appointment_id: int) -> None:
        assert client.post(f"{API}/appointments/{appointment_id}/complete", headers=doctor_h).status_code == 422

    def test_no_show_only_after_start_time(
        self, client: TestClient, reception_h: dict, doctor2_h: dict, appointment_id: int, frozen_clock: FrozenClock
    ) -> None:
        url = f"{API}/appointments/{appointment_id}/no-show"
        assert client.post(url, headers=reception_h).status_code == 422
        frozen_clock.set(datetime(2030, 1, 7, 10, 20))
        assert client.post(url, headers=doctor2_h).status_code == 403
        response = client.post(url, headers=reception_h)
        assert response.status_code == 200 and response.json()["status"] == "faltou"
        # Status final: não pode mais ser cancelada nem iniciada.
        assert client.post(url, headers=reception_h).status_code == 422


class TestListing:
    @pytest.fixture
    def agenda(
        self, db: Session, patient: Patient, other_patient: Patient, doctor: Professional, doctor2: Professional
    ) -> None:
        make_appointment(db, patient, doctor, datetime(2030, 1, 8, 10, 0))
        make_appointment(db, other_patient, doctor, datetime(2030, 1, 8, 8, 30))
        make_appointment(db, other_patient, doctor, datetime(2030, 1, 8, 9, 0), status=AppointmentStatus.CANCELLED)
        make_appointment(db, patient, doctor2, datetime(2030, 1, 9, 14, 0))

    def test_daily_agenda_sorted_without_cancelled(
        self, client: TestClient, doctor_h: dict, doctor: Professional, agenda: None
    ) -> None:
        response = client.get(
            f"{API}/professionals/{doctor.id}/agenda", params={"date": "2030-01-08"}, headers=doctor_h
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        assert [a["start_at"][11:16] for a in body["appointments"]] == ["08:30", "10:00"]
        full = client.get(
            f"{API}/professionals/{doctor.id}/agenda",
            params={"date": "2030-01-08", "include_cancelled": True},
            headers=doctor_h,
        )
        assert full.json()["total"] == 3

    def test_patient_cannot_see_doctor_agenda(self, client: TestClient, patient_h: dict, doctor: Professional) -> None:
        response = client.get(
            f"{API}/professionals/{doctor.id}/agenda", params={"date": "2030-01-08"}, headers=patient_h
        )
        assert response.status_code == 403

    def test_list_with_filters(self, client: TestClient, reception_h: dict, doctor: Professional, agenda: None) -> None:
        by_doctor = client.get(f"{API}/appointments", params={"professional_id": doctor.id}, headers=reception_h).json()
        assert by_doctor["total"] == 3
        cancelled = client.get(f"{API}/appointments", params={"status": "cancelada"}, headers=reception_h).json()
        assert cancelled["total"] == 1
        by_date = client.get(
            f"{API}/appointments", params={"date_from": "2030-01-09", "date_to": "2030-01-09"}, headers=reception_h
        ).json()
        assert by_date["total"] == 1
        desc = client.get(f"{API}/appointments", params={"sort_order": "desc"}, headers=reception_h).json()
        assert desc["items"][0]["start_at"] == "2030-01-09T14:00:00"

    def test_patient_only_lists_own_appointments(
        self, client: TestClient, patient_h: dict, patient: Patient, other_patient: Patient, agenda: None
    ) -> None:
        # Mesmo tentando filtrar por outro paciente, o escopo é forçado para o próprio.
        response = client.get(f"{API}/appointments", params={"patient_id": other_patient.id}, headers=patient_h)
        assert {a["patient_id"] for a in response.json()["items"]} == {patient.id}
        assert response.json()["total"] == 2

    def test_invalid_filters(self, client: TestClient, reception_h: dict) -> None:
        assert client.get(f"{API}/appointments", params={"status": "perdida"}, headers=reception_h).status_code == 422
        bad_range = client.get(
            f"{API}/appointments", params={"date_from": "2030-02-01", "date_to": "2030-01-01"}, headers=reception_h
        )
        assert bad_range.status_code == 422
