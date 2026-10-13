"""Testes de agendamento: conflitos, disponibilidade, ciclo de vida e lista de espera."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus
from tests.conftest import API, auth_headers, next_weekday_at, past_datetime


def schedule_appointment(client, headers, scenario, start=None, **overrides):
    payload = {
        "patient_id": scenario["patient"].id,
        "professional_id": scenario["doctor"].id,
        "scheduled_start": (start or next_weekday_at(9)).isoformat(),
        "reason": "Consulta de rotina",
    }
    payload.update(overrides)
    return client.post(f"{API}/appointments", json=payload, headers=headers)


@pytest.fixture()
def reception_headers(client, scenario):
    return auth_headers(client, "recepcao@clinica.com")


@pytest.fixture()
def doctor_headers(client, scenario):
    return auth_headers(client, "medico@clinica.com")


@pytest.fixture()
def patient_headers(client, scenario):
    return auth_headers(client, "paciente@clinica.com")


class TestCreateAppointment:
    def test_receptionist_schedules(self, client, scenario, reception_headers):
        response = schedule_appointment(client, reception_headers, scenario)
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["status"] == AppointmentStatus.SCHEDULED.value
        assert body["duration_minutes"] == 30
        assert body["scheduled_end"].endswith("09:30:00")

    def test_patient_schedules_for_self(self, client, scenario, patient_headers):
        response = client.post(
            f"{API}/appointments",
            json={
                "professional_id": scenario["doctor"].id,
                "scheduled_start": next_weekday_at(10).isoformat(),
            },
            headers=patient_headers,
        )
        assert response.status_code == 201
        assert response.json()["patient_id"] == scenario["patient"].id

    def test_patient_cannot_schedule_for_another(self, client, scenario, patient_headers):
        response = client.post(
            f"{API}/appointments",
            json={
                "patient_id": scenario["other_patient"].id,
                "professional_id": scenario["doctor"].id,
                "scheduled_start": next_weekday_at(10).isoformat(),
            },
            headers=patient_headers,
        )
        assert response.status_code == 403

    def test_staff_must_inform_patient_id(self, client, scenario, reception_headers):
        response = client.post(
            f"{API}/appointments",
            json={
                "professional_id": scenario["doctor"].id,
                "scheduled_start": next_weekday_at(10).isoformat(),
            },
            headers=reception_headers,
        )
        assert response.status_code == 422

    def test_rejects_double_booking_same_slot(self, client, scenario, reception_headers):
        schedule_appointment(client, reception_headers, scenario)
        response = client.post(
            f"{API}/appointments",
            json={
                "patient_id": scenario["other_patient"].id,
                "professional_id": scenario["doctor"].id,
                "scheduled_start": next_weekday_at(9).isoformat(),
            },
            headers=reception_headers,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "schedule_conflict"

    def test_rejects_overlapping_slot(self, client, scenario, reception_headers):
        schedule_appointment(client, reception_headers, scenario)
        response = client.post(
            f"{API}/appointments",
            json={
                "patient_id": scenario["other_patient"].id,
                "professional_id": scenario["doctor"].id,
                "scheduled_start": next_weekday_at(9, 15).isoformat(),
            },
            headers=reception_headers,
        )
        assert response.status_code == 409

    def test_allows_adjacent_slot(self, client, scenario, reception_headers):
        schedule_appointment(client, reception_headers, scenario)
        response = client.post(
            f"{API}/appointments",
            json={
                "patient_id": scenario["other_patient"].id,
                "professional_id": scenario["doctor"].id,
                "scheduled_start": next_weekday_at(9, 30).isoformat(),
            },
            headers=reception_headers,
        )
        assert response.status_code == 201

    def test_cancelled_slot_is_free_again(self, client, scenario, reception_headers):
        first = schedule_appointment(client, reception_headers, scenario).json()
        client.post(
            f"{API}/appointments/{first['id']}/cancel",
            json={"reason": "Paciente desistiu"},
            headers=reception_headers,
        )
        response = client.post(
            f"{API}/appointments",
            json={
                "patient_id": scenario["other_patient"].id,
                "professional_id": scenario["doctor"].id,
                "scheduled_start": next_weekday_at(9).isoformat(),
            },
            headers=reception_headers,
        )
        assert response.status_code == 201

    def test_rejects_outside_availability_window(self, client, scenario, reception_headers):
        response = schedule_appointment(
            client, reception_headers, scenario, start=next_weekday_at(19)
        )
        assert response.status_code == 422
        assert "available_windows" in response.json()["error"]["details"]

    def test_rejects_weekend(self, client, scenario, reception_headers):
        saturday = next_weekday_at(9) + timedelta(days=5)
        response = schedule_appointment(client, reception_headers, scenario, start=saturday)
        assert response.status_code == 422

    def test_rejects_appointment_crossing_end_of_window(
        self, client, scenario, reception_headers
    ):
        response = schedule_appointment(
            client, reception_headers, scenario, start=next_weekday_at(17, 45)
        )
        assert response.status_code == 422

    def test_rejects_past_datetime(self, client, scenario, reception_headers):
        response = schedule_appointment(
            client, reception_headers, scenario, start=past_datetime()
        )
        assert response.status_code == 422
        assert "passado" in response.json()["error"]["message"].lower()

    def test_rejects_patient_double_booking_with_other_doctor(
        self, client, scenario, reception_headers
    ):
        schedule_appointment(client, reception_headers, scenario)
        response = client.post(
            f"{API}/appointments",
            json={
                "patient_id": scenario["patient"].id,
                "professional_id": scenario["other_doctor"].id,
                "scheduled_start": next_weekday_at(9).isoformat(),
            },
            headers=reception_headers,
        )
        assert response.status_code == 409

    def test_rejects_nurse_as_professional(self, client, scenario, reception_headers):
        response = client.post(
            f"{API}/appointments",
            json={
                "patient_id": scenario["patient"].id,
                "professional_id": scenario["nurse"].id,
                "scheduled_start": next_weekday_at(9).isoformat(),
            },
            headers=reception_headers,
        )
        assert response.status_code == 422

    def test_rejects_unknown_professional(self, client, scenario, reception_headers):
        response = client.post(
            f"{API}/appointments",
            json={
                "patient_id": scenario["patient"].id,
                "professional_id": 9999,
                "scheduled_start": next_weekday_at(9).isoformat(),
            },
            headers=reception_headers,
        )
        assert response.status_code == 404

    def test_rejects_inactive_patient(self, client, db, scenario, reception_headers):
        admin_headers = auth_headers(client, "admin@clinica.com")
        client.delete(f"{API}/patients/{scenario['patient'].id}", headers=admin_headers)
        response = schedule_appointment(client, reception_headers, scenario)
        assert response.status_code == 422


class TestAppointmentLifecycle:
    def test_confirm(self, client, scenario, reception_headers):
        appointment = schedule_appointment(client, reception_headers, scenario).json()
        response = client.post(
            f"{API}/appointments/{appointment['id']}/confirm", headers=reception_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == AppointmentStatus.CONFIRMED.value
        assert response.json()["confirmed_at"] is not None

    def test_cannot_confirm_twice(self, client, scenario, reception_headers):
        appointment = schedule_appointment(client, reception_headers, scenario).json()
        client.post(f"{API}/appointments/{appointment['id']}/confirm", headers=reception_headers)
        response = client.post(
            f"{API}/appointments/{appointment['id']}/confirm", headers=reception_headers
        )
        assert response.status_code == 409

    def test_cancel_requires_reason(self, client, scenario, reception_headers):
        appointment = schedule_appointment(client, reception_headers, scenario).json()
        response = client.post(
            f"{API}/appointments/{appointment['id']}/cancel", json={}, headers=reception_headers
        )
        assert response.status_code == 422

    def test_cancel_records_reason_and_author(self, client, scenario, reception_headers):
        appointment = schedule_appointment(client, reception_headers, scenario).json()
        response = client.post(
            f"{API}/appointments/{appointment['id']}/cancel",
            json={"reason": "Medico em congresso"},
            headers=reception_headers,
        )
        body = response.json()
        assert body["status"] == AppointmentStatus.CANCELLED.value
        assert body["cancellation_reason"] == "Medico em congresso"
        assert body["cancelled_by_id"] == scenario["receptionist"].id

    def test_cannot_cancel_twice(self, client, scenario, reception_headers):
        appointment = schedule_appointment(client, reception_headers, scenario).json()
        client.post(
            f"{API}/appointments/{appointment['id']}/cancel",
            json={"reason": "Motivo"},
            headers=reception_headers,
        )
        response = client.post(
            f"{API}/appointments/{appointment['id']}/cancel",
            json={"reason": "Outro motivo"},
            headers=reception_headers,
        )
        assert response.status_code == 409

    def test_reschedule_to_free_slot(self, client, scenario, reception_headers):
        appointment = schedule_appointment(client, reception_headers, scenario).json()
        new_start = next_weekday_at(11)
        response = client.post(
            f"{API}/appointments/{appointment['id']}/reschedule",
            json={"scheduled_start": new_start.isoformat(), "reason": "Pedido do paciente"},
            headers=reception_headers,
        )
        assert response.status_code == 200
        assert response.json()["scheduled_start"].endswith("11:00:00")
        assert response.json()["status"] == AppointmentStatus.SCHEDULED.value

    def test_reschedule_rejects_conflict(self, client, scenario, reception_headers):
        first = schedule_appointment(client, reception_headers, scenario).json()
        client.post(
            f"{API}/appointments",
            json={
                "patient_id": scenario["other_patient"].id,
                "professional_id": scenario["doctor"].id,
                "scheduled_start": next_weekday_at(11).isoformat(),
            },
            headers=reception_headers,
        )
        response = client.post(
            f"{API}/appointments/{first['id']}/reschedule",
            json={"scheduled_start": next_weekday_at(11).isoformat()},
            headers=reception_headers,
        )
        assert response.status_code == 409

    def test_reschedule_rejects_past(self, client, scenario, reception_headers):
        appointment = schedule_appointment(client, reception_headers, scenario).json()
        response = client.post(
            f"{API}/appointments/{appointment['id']}/reschedule",
            json={"scheduled_start": past_datetime().isoformat()},
            headers=reception_headers,
        )
        assert response.status_code == 422

    def test_cannot_reschedule_cancelled(self, client, scenario, reception_headers):
        appointment = schedule_appointment(client, reception_headers, scenario).json()
        client.post(
            f"{API}/appointments/{appointment['id']}/cancel",
            json={"reason": "Motivo"},
            headers=reception_headers,
        )
        response = client.post(
            f"{API}/appointments/{appointment['id']}/reschedule",
            json={"scheduled_start": next_weekday_at(11).isoformat()},
            headers=reception_headers,
        )
        assert response.status_code == 422

    def test_doctor_starts_and_completes(self, client, scenario, reception_headers, doctor_headers):
        appointment = schedule_appointment(client, reception_headers, scenario).json()
        started = client.post(
            f"{API}/appointments/{appointment['id']}/start", headers=doctor_headers
        )
        assert started.status_code == 200
        assert started.json()["status"] == AppointmentStatus.IN_PROGRESS.value

        completed = client.post(
            f"{API}/appointments/{appointment['id']}/complete", headers=doctor_headers
        )
        assert completed.status_code == 200
        assert completed.json()["status"] == AppointmentStatus.COMPLETED.value

    def test_only_responsible_doctor_can_start(self, client, scenario, reception_headers):
        appointment = schedule_appointment(client, reception_headers, scenario).json()
        other = auth_headers(client, "medico2@clinica.com")
        response = client.post(
            f"{API}/appointments/{appointment['id']}/start", headers=other
        )
        assert response.status_code == 403

    def test_receptionist_cannot_start(self, client, scenario, reception_headers):
        appointment = schedule_appointment(client, reception_headers, scenario).json()
        response = client.post(
            f"{API}/appointments/{appointment['id']}/start", headers=reception_headers
        )
        assert response.status_code == 403

    def test_cannot_complete_without_starting(self, client, scenario, reception_headers, doctor_headers):
        appointment = schedule_appointment(client, reception_headers, scenario).json()
        response = client.post(
            f"{API}/appointments/{appointment['id']}/complete", headers=doctor_headers
        )
        assert response.status_code == 422

    def test_completed_appointment_is_immutable(self, client, db, scenario, reception_headers, doctor_headers):
        appointment = schedule_appointment(client, reception_headers, scenario).json()
        client.post(f"{API}/appointments/{appointment['id']}/start", headers=doctor_headers)
        client.post(f"{API}/appointments/{appointment['id']}/complete", headers=doctor_headers)
        response = client.patch(
            f"{API}/appointments/{appointment['id']}",
            json={"notes": "tentativa"},
            headers=reception_headers,
        )
        assert response.status_code == 422

    def test_no_show_requires_past_schedule(self, client, scenario, reception_headers):
        appointment = schedule_appointment(client, reception_headers, scenario).json()
        response = client.post(
            f"{API}/appointments/{appointment['id']}/no-show", headers=reception_headers
        )
        assert response.status_code == 422

    def test_no_show_registered_for_past_appointment(
        self, client, db, scenario, reception_headers
    ):
        appointment = schedule_appointment(client, reception_headers, scenario).json()
        stored = db.get(Appointment, appointment["id"])
        stored.scheduled_start = past_datetime()
        stored.scheduled_end = past_datetime() + timedelta(minutes=30)
        db.commit()
        response = client.post(
            f"{API}/appointments/{appointment['id']}/no-show", headers=reception_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == AppointmentStatus.NO_SHOW.value

    def test_patient_cannot_register_no_show(self, client, db, scenario, reception_headers, patient_headers):
        appointment = schedule_appointment(client, reception_headers, scenario).json()
        stored = db.get(Appointment, appointment["id"])
        stored.scheduled_start = past_datetime()
        db.commit()
        response = client.post(
            f"{API}/appointments/{appointment['id']}/no-show", headers=patient_headers
        )
        assert response.status_code == 403


class TestAppointmentAccessControl:
    def test_patient_sees_only_own_appointments(self, client, scenario, reception_headers, patient_headers):
        schedule_appointment(client, reception_headers, scenario)
        client.post(
            f"{API}/appointments",
            json={
                "patient_id": scenario["other_patient"].id,
                "professional_id": scenario["doctor"].id,
                "scheduled_start": next_weekday_at(10).isoformat(),
            },
            headers=reception_headers,
        )
        response = client.get(f"{API}/appointments", headers=patient_headers)
        assert response.json()["meta"]["total"] == 1

    def test_patient_cannot_read_other_appointment(self, client, scenario, reception_headers, patient_headers):
        other = client.post(
            f"{API}/appointments",
            json={
                "patient_id": scenario["other_patient"].id,
                "professional_id": scenario["doctor"].id,
                "scheduled_start": next_weekday_at(10).isoformat(),
            },
            headers=reception_headers,
        ).json()
        response = client.get(f"{API}/appointments/{other['id']}", headers=patient_headers)
        assert response.status_code == 403

    def test_doctor_sees_only_own_agenda(self, client, scenario, reception_headers, doctor_headers):
        schedule_appointment(client, reception_headers, scenario)
        client.post(
            f"{API}/appointments",
            json={
                "patient_id": scenario["other_patient"].id,
                "professional_id": scenario["other_doctor"].id,
                "scheduled_start": next_weekday_at(10).isoformat(),
            },
            headers=reception_headers,
        )
        response = client.get(f"{API}/appointments", headers=doctor_headers)
        assert response.json()["meta"]["total"] == 1

    def test_doctor_cannot_query_colleague_agenda(self, client, scenario, doctor_headers):
        response = client.get(
            f"{API}/appointments",
            params={"professional_id": scenario["other_doctor"].id},
            headers=doctor_headers,
        )
        assert response.status_code == 403

    def test_filter_by_status_and_period(self, client, scenario, reception_headers):
        appointment = schedule_appointment(client, reception_headers, scenario).json()
        client.post(f"{API}/appointments/{appointment['id']}/confirm", headers=reception_headers)
        response = client.get(
            f"{API}/appointments",
            params={"status": "confirmed", "start_date": next_weekday_at(9).date().isoformat()},
            headers=reception_headers,
        )
        assert response.json()["meta"]["total"] == 1


class TestDailyAgenda:
    def test_returns_appointments_of_the_day(self, client, scenario, reception_headers):
        schedule_appointment(client, reception_headers, scenario)
        target = next_weekday_at(9)
        response = client.get(
            f"{API}/professionals/{scenario['doctor'].id}/agenda",
            params={"date": target.date().isoformat()},
            headers=reception_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["appointments"][0]["patient_name"] == "Maria Silva"

    def test_doctor_reads_own_agenda(self, client, scenario, reception_headers, doctor_headers):
        schedule_appointment(client, reception_headers, scenario)
        target = next_weekday_at(9)
        response = client.get(
            f"{API}/professionals/{scenario['doctor'].id}/agenda",
            params={"date": target.date().isoformat()},
            headers=doctor_headers,
        )
        assert response.status_code == 200

    def test_doctor_cannot_read_colleague_agenda(self, client, scenario, doctor_headers):
        target = next_weekday_at(9)
        response = client.get(
            f"{API}/professionals/{scenario['other_doctor'].id}/agenda",
            params={"date": target.date().isoformat()},
            headers=doctor_headers,
        )
        assert response.status_code == 403

    def test_patient_cannot_read_agenda(self, client, scenario, patient_headers):
        target = next_weekday_at(9)
        response = client.get(
            f"{API}/professionals/{scenario['doctor'].id}/agenda",
            params={"date": target.date().isoformat()},
            headers=patient_headers,
        )
        assert response.status_code == 403


class TestWaitlist:
    def test_patient_joins_waitlist(self, client, scenario, patient_headers):
        response = client.post(
            f"{API}/waitlist",
            json={
                "professional_id": scenario["doctor"].id,
                "desired_date": next_weekday_at(9).date().isoformat(),
            },
            headers=patient_headers,
        )
        assert response.status_code == 201
        assert response.json()["status"] == "waiting"

    def test_rejects_duplicate_entry(self, client, scenario, patient_headers):
        payload = {
            "professional_id": scenario["doctor"].id,
            "desired_date": next_weekday_at(9).date().isoformat(),
        }
        client.post(f"{API}/waitlist", json=payload, headers=patient_headers)
        response = client.post(f"{API}/waitlist", json=payload, headers=patient_headers)
        assert response.status_code == 409

    def test_rejects_past_date(self, client, scenario, patient_headers):
        response = client.post(
            f"{API}/waitlist",
            json={
                "professional_id": scenario["doctor"].id,
                "desired_date": past_datetime().date().isoformat(),
            },
            headers=patient_headers,
        )
        assert response.status_code == 422

    def test_notifies_when_slot_is_released(self, client, scenario, reception_headers):
        target = next_weekday_at(9)
        appointment = schedule_appointment(client, reception_headers, scenario).json()

        other_patient_headers = auth_headers(client, "paciente2@clinica.com")
        client.post(
            f"{API}/waitlist",
            json={
                "professional_id": scenario["doctor"].id,
                "desired_date": target.date().isoformat(),
            },
            headers=other_patient_headers,
        )

        client.post(
            f"{API}/appointments/{appointment['id']}/cancel",
            json={"reason": "Paciente desistiu"},
            headers=reception_headers,
        )

        notifications = client.get(
            f"{API}/notifications", headers=other_patient_headers
        ).json()
        types = [item["notification_type"] for item in notifications["items"]]
        assert "waitlist_slot_available" in types

        entries = client.get(f"{API}/waitlist", headers=other_patient_headers).json()
        assert entries["items"][0]["status"] == "notified"

    def test_does_not_notify_outside_preferred_window(self, client, scenario, reception_headers):
        target = next_weekday_at(9)
        appointment = schedule_appointment(client, reception_headers, scenario).json()
        other_patient_headers = auth_headers(client, "paciente2@clinica.com")
        client.post(
            f"{API}/waitlist",
            json={
                "professional_id": scenario["doctor"].id,
                "desired_date": target.date().isoformat(),
                "preferred_start_time": "14:00:00",
                "preferred_end_time": "17:00:00",
            },
            headers=other_patient_headers,
        )
        client.post(
            f"{API}/appointments/{appointment['id']}/cancel",
            json={"reason": "Paciente desistiu"},
            headers=reception_headers,
        )
        entries = client.get(f"{API}/waitlist", headers=other_patient_headers).json()
        assert entries["items"][0]["status"] == "waiting"

    def test_entry_is_fulfilled_when_patient_books(self, client, scenario, reception_headers, patient_headers):
        target = next_weekday_at(9)
        client.post(
            f"{API}/waitlist",
            json={
                "professional_id": scenario["doctor"].id,
                "desired_date": target.date().isoformat(),
            },
            headers=patient_headers,
        )
        schedule_appointment(client, reception_headers, scenario)
        entries = client.get(f"{API}/waitlist", headers=patient_headers).json()
        assert entries["items"][0]["status"] == "fulfilled"

    def test_patient_leaves_waitlist(self, client, scenario, patient_headers):
        entry = client.post(
            f"{API}/waitlist",
            json={
                "professional_id": scenario["doctor"].id,
                "desired_date": next_weekday_at(9).date().isoformat(),
            },
            headers=patient_headers,
        ).json()
        response = client.delete(f"{API}/waitlist/{entry['id']}", headers=patient_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_patient_cannot_remove_other_entry(self, client, scenario, patient_headers):
        other_headers = auth_headers(client, "paciente2@clinica.com")
        entry = client.post(
            f"{API}/waitlist",
            json={
                "professional_id": scenario["doctor"].id,
                "desired_date": next_weekday_at(9).date().isoformat(),
            },
            headers=other_headers,
        ).json()
        response = client.delete(f"{API}/waitlist/{entry['id']}", headers=patient_headers)
        assert response.status_code == 403
