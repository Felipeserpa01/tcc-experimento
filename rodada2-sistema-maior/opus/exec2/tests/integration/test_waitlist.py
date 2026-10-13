from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.professional import Professional
from tests.conftest import FakeEmailSender, FrozenClock
from tests.factories import API, make_patient, token_for

SLOT = "2030-01-08T09:00:00"


@pytest.fixture
def occupied_slot(client: TestClient, reception_h: dict, other_patient: Patient, doctor: Professional) -> int:
    response = client.post(
        f"{API}/appointments",
        json={"patient_id": other_patient.id, "professional_id": doctor.id, "start_at": SLOT},
        headers=reception_h,
    )
    assert response.status_code == 201
    return response.json()["id"]


def join(client: TestClient, headers: dict, doctor_id: int, start: str = SLOT, patient_id: int | None = None):
    payload: dict = {"professional_id": doctor_id, "start_at": start}
    if patient_id:
        payload["patient_id"] = patient_id
    return client.post(f"{API}/waitlist", json=payload, headers=headers)


class TestWaitlist:
    def test_cannot_join_waitlist_for_free_slot(
        self, client: TestClient, patient_h: dict, doctor: Professional
    ) -> None:
        response = join(client, patient_h, doctor.id)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "horario_disponivel"

    def test_join_occupied_slot(
        self, client: TestClient, patient_h: dict, patient: Patient, doctor: Professional, occupied_slot: int
    ) -> None:
        response = join(client, patient_h, doctor.id)
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "aguardando"
        assert body["patient_id"] == patient.id
        assert body["desired_end_at"] == "2030-01-08T09:30:00"

    def test_duplicate_entry(
        self, client: TestClient, patient_h: dict, doctor: Professional, occupied_slot: int
    ) -> None:
        assert join(client, patient_h, doctor.id).status_code == 201
        assert join(client, patient_h, doctor.id).status_code == 409

    def test_patient_holding_the_slot_cannot_join(
        self, client: TestClient, other_patient_h: dict, doctor: Professional, occupied_slot: int
    ) -> None:
        assert join(client, other_patient_h, doctor.id).status_code == 409

    def test_waitlist_validates_schedule(
        self, client: TestClient, patient_h: dict, doctor: Professional, occupied_slot: int
    ) -> None:
        assert join(client, patient_h, doctor.id, "2030-01-12T09:00:00").status_code == 422
        assert join(client, patient_h, doctor.id, "2030-01-06T09:00:00").status_code == 422

    def test_cancellation_notifies_waiting_patients_in_order(
        self,
        client: TestClient,
        db: Session,
        reception_h: dict,
        patient: Patient,
        patient_h: dict,
        doctor: Professional,
        occupied_slot: int,
        mailer: FakeEmailSender,
    ) -> None:
        third = make_patient(db, full_name="Terceiro Paciente", with_user=True, email="terceiro@clinica.com.br")
        assert join(client, patient_h, doctor.id).status_code == 201
        assert join(client, token_for(third.user), doctor.id).status_code == 201
        mailer.outbox.clear()

        cancel = client.post(
            f"{API}/appointments/{occupied_slot}/cancel", json={"reason": "Imprevisto no trabalho"}, headers=reception_h
        )
        assert cancel.status_code == 200

        entries = client.get(f"{API}/waitlist", params={"sort_by": "created_at"}, headers=reception_h).json()["items"]
        assert [e["status"] for e in entries] == ["notificado", "notificado"]
        assert {m.to for m in mailer.outbox} == {"maria@clinica.com.br", "terceiro@clinica.com.br"}
        first_message = next(m for m in mailer.outbox if m.to == "maria@clinica.com.br")
        assert "1º da lista" in first_message.body

        notifications = client.get(f"{API}/notifications", headers=patient_h).json()
        assert notifications["items"][0]["subject"] == "Horário disponível"

    def test_booking_freed_slot_marks_entry_as_booked(
        self,
        client: TestClient,
        reception_h: dict,
        patient_h: dict,
        doctor: Professional,
        occupied_slot: int,
    ) -> None:
        entry_id = join(client, patient_h, doctor.id).json()["id"]
        client.post(f"{API}/appointments/{occupied_slot}/cancel", json={"reason": "Desistência"}, headers=reception_h)
        booked = client.post(
            f"{API}/appointments", json={"professional_id": doctor.id, "start_at": SLOT}, headers=patient_h
        )
        assert booked.status_code == 201
        assert client.get(f"{API}/waitlist/{entry_id}", headers=patient_h).json()["status"] == "agendado"

    def test_reschedule_releases_old_slot_to_waitlist(
        self, client: TestClient, reception_h: dict, patient_h: dict, doctor: Professional, occupied_slot: int
    ) -> None:
        entry_id = join(client, patient_h, doctor.id).json()["id"]
        client.post(
            f"{API}/appointments/{occupied_slot}/reschedule",
            json={"start_at": "2030-01-10T09:00:00"},
            headers=reception_h,
        )
        assert client.get(f"{API}/waitlist/{entry_id}", headers=patient_h).json()["status"] == "notificado"

    def test_patient_scope_and_cancel(
        self,
        client: TestClient,
        patient_h: dict,
        other_patient_h: dict,
        doctor: Professional,
        occupied_slot: int,
    ) -> None:
        entry_id = join(client, patient_h, doctor.id).json()["id"]
        assert client.get(f"{API}/waitlist/{entry_id}", headers=other_patient_h).status_code == 403
        assert client.post(f"{API}/waitlist/{entry_id}/cancel", headers=other_patient_h).status_code == 403
        cancelled = client.post(f"{API}/waitlist/{entry_id}/cancel", headers=patient_h)
        assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelado"
        assert client.post(f"{API}/waitlist/{entry_id}/cancel", headers=patient_h).status_code == 422
        assert client.get(f"{API}/waitlist", headers=other_patient_h).json()["total"] == 0

    def test_past_entries_expire(
        self,
        client: TestClient,
        patient_h: dict,
        doctor: Professional,
        occupied_slot: int,
        frozen_clock: FrozenClock,
    ) -> None:
        join(client, patient_h, doctor.id)
        frozen_clock.set(datetime(2030, 1, 8, 9, 30))
        entries = client.get(f"{API}/waitlist", headers=patient_h).json()["items"]
        assert entries[0]["status"] == "expirado"


class TestNotifications:
    def test_scheduling_creates_notification_and_mark_read(
        self, client: TestClient, patient_h: dict, doctor: Professional, mailer: FakeEmailSender
    ) -> None:
        client.post(f"{API}/appointments", json={"professional_id": doctor.id, "start_at": SLOT}, headers=patient_h)
        assert mailer.outbox[0].subject == "Consulta agendada"
        listing = client.get(f"{API}/notifications", params={"unread_only": True}, headers=patient_h).json()
        assert listing["total"] == 1
        notification_id = listing["items"][0]["id"]
        read = client.post(f"{API}/notifications/{notification_id}/read", headers=patient_h)
        assert read.status_code == 200 and read.json()["read_at"] is not None
        assert client.get(f"{API}/notifications", params={"unread_only": True}, headers=patient_h).json()["total"] == 0

    def test_cannot_read_notifications_of_others(
        self, client: TestClient, patient_h: dict, other_patient_h: dict, doctor: Professional
    ) -> None:
        client.post(f"{API}/appointments", json={"professional_id": doctor.id, "start_at": SLOT}, headers=patient_h)
        notification_id = client.get(f"{API}/notifications", headers=patient_h).json()["items"][0]["id"]
        assert client.post(f"{API}/notifications/{notification_id}/read", headers=other_patient_h).status_code == 404
        assert client.post(f"{API}/notifications/read-all", headers=patient_h).status_code == 204
