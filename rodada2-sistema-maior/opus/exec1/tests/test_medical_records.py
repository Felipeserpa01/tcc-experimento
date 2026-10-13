"""Testes de prontuario, prescricoes, exames e historico clinico."""

from __future__ import annotations

import io

import pytest

from tests.conftest import API, auth_headers, next_weekday_at


RECORD_PAYLOAD = {
    "chief_complaint": "Dor toracica ha 3 dias",
    "history": "Sem historico previo de cardiopatia",
    "diagnosis": "Angina estavel",
    "icd10_code": "I20.9",
    "treatment_plan": "Uso de AAS e acompanhamento",
    "observations": "Retorno em 30 dias",
    "blood_pressure": "130/85",
    "heart_rate": 78,
    "temperature_celsius": "36.5",
    "weight_kg": "72.50",
    "height_cm": "168.0",
}


@pytest.fixture()
def reception_headers(client, scenario):
    return auth_headers(client, "recepcao@clinica.com")


@pytest.fixture()
def doctor_headers(client, scenario):
    return auth_headers(client, "medico@clinica.com")


@pytest.fixture()
def patient_headers(client, scenario):
    return auth_headers(client, "paciente@clinica.com")


@pytest.fixture()
def in_progress_appointment(client, scenario, reception_headers, doctor_headers):
    appointment = client.post(
        f"{API}/appointments",
        json={
            "patient_id": scenario["patient"].id,
            "professional_id": scenario["doctor"].id,
            "scheduled_start": next_weekday_at(9).isoformat(),
            "reason": "Dor toracica",
        },
        headers=reception_headers,
    ).json()
    client.post(f"{API}/appointments/{appointment['id']}/start", headers=doctor_headers)
    return appointment


class TestMedicalRecord:
    def test_responsible_doctor_creates_record(
        self, client, in_progress_appointment, doctor_headers
    ):
        response = client.post(
            f"{API}/appointments/{in_progress_appointment['id']}/medical-record",
            json=RECORD_PAYLOAD,
            headers=doctor_headers,
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["diagnosis"] == "Angina estavel"
        assert body["appointment_id"] == in_progress_appointment["id"]

    def test_other_doctor_cannot_create(self, client, in_progress_appointment, scenario):
        other = auth_headers(client, "medico2@clinica.com")
        response = client.post(
            f"{API}/appointments/{in_progress_appointment['id']}/medical-record",
            json=RECORD_PAYLOAD,
            headers=other,
        )
        assert response.status_code == 403

    def test_nurse_cannot_create(self, client, in_progress_appointment):
        nurse = auth_headers(client, "enfermeiro@clinica.com")
        response = client.post(
            f"{API}/appointments/{in_progress_appointment['id']}/medical-record",
            json=RECORD_PAYLOAD,
            headers=nurse,
        )
        assert response.status_code == 403

    def test_patient_cannot_create(self, client, in_progress_appointment, patient_headers):
        response = client.post(
            f"{API}/appointments/{in_progress_appointment['id']}/medical-record",
            json=RECORD_PAYLOAD,
            headers=patient_headers,
        )
        assert response.status_code == 403

    def test_cannot_create_twice(self, client, in_progress_appointment, doctor_headers):
        client.post(
            f"{API}/appointments/{in_progress_appointment['id']}/medical-record",
            json=RECORD_PAYLOAD,
            headers=doctor_headers,
        )
        response = client.post(
            f"{API}/appointments/{in_progress_appointment['id']}/medical-record",
            json=RECORD_PAYLOAD,
            headers=doctor_headers,
        )
        assert response.status_code == 409

    def test_cannot_create_for_scheduled_appointment(
        self, client, scenario, reception_headers, doctor_headers
    ):
        appointment = client.post(
            f"{API}/appointments",
            json={
                "patient_id": scenario["patient"].id,
                "professional_id": scenario["doctor"].id,
                "scheduled_start": next_weekday_at(10).isoformat(),
            },
            headers=reception_headers,
        ).json()
        response = client.post(
            f"{API}/appointments/{appointment['id']}/medical-record",
            json=RECORD_PAYLOAD,
            headers=doctor_headers,
        )
        assert response.status_code == 422

    def test_requires_complaint_and_diagnosis(
        self, client, in_progress_appointment, doctor_headers
    ):
        response = client.post(
            f"{API}/appointments/{in_progress_appointment['id']}/medical-record",
            json={"chief_complaint": "Dor"},
            headers=doctor_headers,
        )
        assert response.status_code == 422

    def test_rejects_impossible_vital_signs(
        self, client, in_progress_appointment, doctor_headers
    ):
        payload = dict(RECORD_PAYLOAD, heart_rate=900)
        response = client.post(
            f"{API}/appointments/{in_progress_appointment['id']}/medical-record",
            json=payload,
            headers=doctor_headers,
        )
        assert response.status_code == 422

    def test_patient_reads_own_record(
        self, client, in_progress_appointment, doctor_headers, patient_headers
    ):
        client.post(
            f"{API}/appointments/{in_progress_appointment['id']}/medical-record",
            json=RECORD_PAYLOAD,
            headers=doctor_headers,
        )
        response = client.get(
            f"{API}/appointments/{in_progress_appointment['id']}/medical-record",
            headers=patient_headers,
        )
        assert response.status_code == 200
        assert response.json()["diagnosis"] == "Angina estavel"

    def test_other_patient_cannot_read(
        self, client, in_progress_appointment, doctor_headers
    ):
        client.post(
            f"{API}/appointments/{in_progress_appointment['id']}/medical-record",
            json=RECORD_PAYLOAD,
            headers=doctor_headers,
        )
        other = auth_headers(client, "paciente2@clinica.com")
        response = client.get(
            f"{API}/appointments/{in_progress_appointment['id']}/medical-record", headers=other
        )
        assert response.status_code == 403

    def test_patient_cannot_edit_record(
        self, client, in_progress_appointment, doctor_headers, patient_headers
    ):
        record = client.post(
            f"{API}/appointments/{in_progress_appointment['id']}/medical-record",
            json=RECORD_PAYLOAD,
            headers=doctor_headers,
        ).json()
        response = client.patch(
            f"{API}/medical-records/{record['id']}",
            json={"diagnosis": "Alterado pelo paciente"},
            headers=patient_headers,
        )
        assert response.status_code == 403

    def test_responsible_doctor_updates_record(
        self, client, in_progress_appointment, doctor_headers
    ):
        record = client.post(
            f"{API}/appointments/{in_progress_appointment['id']}/medical-record",
            json=RECORD_PAYLOAD,
            headers=doctor_headers,
        ).json()
        response = client.patch(
            f"{API}/medical-records/{record['id']}",
            json={"observations": "Paciente retornou"},
            headers=doctor_headers,
        )
        assert response.status_code == 200
        assert response.json()["observations"] == "Paciente retornou"

    def test_patient_listing_is_scoped(
        self, client, in_progress_appointment, doctor_headers, patient_headers
    ):
        client.post(
            f"{API}/appointments/{in_progress_appointment['id']}/medical-record",
            json=RECORD_PAYLOAD,
            headers=doctor_headers,
        )
        response = client.get(f"{API}/medical-records", headers=patient_headers)
        assert response.json()["meta"]["total"] == 1


class TestPrescriptions:
    def _create(self, client, appointment_id, headers, **overrides):
        payload = {
            "medication_name": "Losartana",
            "dosage": "50 mg",
            "frequency": "1 vez ao dia",
            "duration": "30 dias",
            "route": "oral",
            "instructions": "Tomar pela manha",
        }
        payload.update(overrides)
        return client.post(
            f"{API}/appointments/{appointment_id}/prescriptions", json=payload, headers=headers
        )

    def test_doctor_creates_prescription(
        self, client, in_progress_appointment, doctor_headers
    ):
        response = self._create(client, in_progress_appointment["id"], doctor_headers)
        assert response.status_code == 201
        assert response.json()["medication_name"] == "Losartana"

    def test_requires_all_mandatory_fields(
        self, client, in_progress_appointment, doctor_headers
    ):
        response = client.post(
            f"{API}/appointments/{in_progress_appointment['id']}/prescriptions",
            json={"medication_name": "Losartana"},
            headers=doctor_headers,
        )
        assert response.status_code == 422

    def test_other_doctor_cannot_prescribe(self, client, in_progress_appointment):
        other = auth_headers(client, "medico2@clinica.com")
        response = self._create(client, in_progress_appointment["id"], other)
        assert response.status_code == 403

    def test_patient_cannot_prescribe(
        self, client, in_progress_appointment, patient_headers
    ):
        response = self._create(client, in_progress_appointment["id"], patient_headers)
        assert response.status_code == 403

    def test_patient_can_read_prescriptions(
        self, client, in_progress_appointment, doctor_headers, patient_headers
    ):
        self._create(client, in_progress_appointment["id"], doctor_headers)
        response = client.get(
            f"{API}/appointments/{in_progress_appointment['id']}/prescriptions",
            headers=patient_headers,
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_prescription_links_to_record(
        self, client, in_progress_appointment, doctor_headers
    ):
        record = client.post(
            f"{API}/appointments/{in_progress_appointment['id']}/medical-record",
            json=RECORD_PAYLOAD,
            headers=doctor_headers,
        ).json()
        prescription = self._create(
            client, in_progress_appointment["id"], doctor_headers
        ).json()
        assert prescription["medical_record_id"] == record["id"]

    def test_prescription_created_before_record_is_relinked(
        self, client, in_progress_appointment, doctor_headers
    ):
        prescription = self._create(
            client, in_progress_appointment["id"], doctor_headers
        ).json()
        assert prescription["medical_record_id"] is None
        record = client.post(
            f"{API}/appointments/{in_progress_appointment['id']}/medical-record",
            json=RECORD_PAYLOAD,
            headers=doctor_headers,
        ).json()
        listing = client.get(
            f"{API}/appointments/{in_progress_appointment['id']}/prescriptions",
            headers=doctor_headers,
        ).json()
        assert listing[0]["medical_record_id"] == record["id"]

    def test_update_and_delete(self, client, in_progress_appointment, doctor_headers):
        prescription = self._create(
            client, in_progress_appointment["id"], doctor_headers
        ).json()
        updated = client.patch(
            f"{API}/prescriptions/{prescription['id']}",
            json={"dosage": "100 mg"},
            headers=doctor_headers,
        )
        assert updated.json()["dosage"] == "100 mg"

        deleted = client.delete(
            f"{API}/prescriptions/{prescription['id']}", headers=doctor_headers
        )
        assert deleted.status_code == 204


class TestExams:
    def _request_exam(self, client, appointment_id, headers, **overrides):
        payload = {
            "exam_name": "Eletrocardiograma",
            "exam_type": "Cardiologico",
            "clinical_indication": "Investigacao de angina",
            "price": "180.00",
        }
        payload.update(overrides)
        return client.post(
            f"{API}/appointments/{appointment_id}/exams", json=payload, headers=headers
        )

    def test_doctor_requests_exam(self, client, in_progress_appointment, doctor_headers):
        response = self._request_exam(client, in_progress_appointment["id"], doctor_headers)
        assert response.status_code == 201
        assert response.json()["status"] == "requested"

    def test_patient_cannot_request_exam(
        self, client, in_progress_appointment, patient_headers
    ):
        response = self._request_exam(client, in_progress_appointment["id"], patient_headers)
        assert response.status_code == 403

    def test_register_result(self, client, in_progress_appointment, doctor_headers):
        exam = self._request_exam(client, in_progress_appointment["id"], doctor_headers).json()
        response = client.post(
            f"{API}/exams/{exam['id']}/result",
            json={"result_summary": "Ritmo sinusal, sem alteracoes"},
            headers=doctor_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "completed"
        assert response.json()["result_registered_at"] is not None

    def test_patient_is_notified_about_result(
        self, client, in_progress_appointment, doctor_headers, patient_headers
    ):
        exam = self._request_exam(client, in_progress_appointment["id"], doctor_headers).json()
        client.post(
            f"{API}/exams/{exam['id']}/result",
            json={"result_summary": "Normal"},
            headers=doctor_headers,
        )
        notifications = client.get(f"{API}/notifications", headers=patient_headers).json()
        types = [item["notification_type"] for item in notifications["items"]]
        assert "exam_result_available" in types

    def test_patient_reads_own_exam(
        self, client, in_progress_appointment, doctor_headers, patient_headers
    ):
        exam = self._request_exam(client, in_progress_appointment["id"], doctor_headers).json()
        response = client.get(f"{API}/exams/{exam['id']}", headers=patient_headers)
        assert response.status_code == 200

    def test_other_patient_cannot_read_exam(
        self, client, in_progress_appointment, doctor_headers
    ):
        exam = self._request_exam(client, in_progress_appointment["id"], doctor_headers).json()
        other = auth_headers(client, "paciente2@clinica.com")
        response = client.get(f"{API}/exams/{exam['id']}", headers=other)
        assert response.status_code == 403

    def test_cancel_requires_reason(self, client, in_progress_appointment, doctor_headers):
        exam = self._request_exam(client, in_progress_appointment["id"], doctor_headers).json()
        response = client.patch(
            f"{API}/exams/{exam['id']}/status",
            json={"status": "cancelled"},
            headers=doctor_headers,
        )
        assert response.status_code == 422

    def test_cancelled_exam_rejects_result(
        self, client, in_progress_appointment, doctor_headers
    ):
        exam = self._request_exam(client, in_progress_appointment["id"], doctor_headers).json()
        client.patch(
            f"{API}/exams/{exam['id']}/status",
            json={"status": "cancelled", "cancellation_reason": "Paciente nao compareceu"},
            headers=doctor_headers,
        )
        response = client.post(
            f"{API}/exams/{exam['id']}/result",
            json={"result_summary": "Normal"},
            headers=doctor_headers,
        )
        assert response.status_code == 409

    def test_attach_result_file(self, client, in_progress_appointment, doctor_headers):
        exam = self._request_exam(client, in_progress_appointment["id"], doctor_headers).json()
        response = client.post(
            f"{API}/exams/{exam['id']}/attachments",
            files={"file": ("resultado.pdf", io.BytesIO(b"%PDF-1.4 conteudo"), "application/pdf")},
            data={"description": "Laudo assinado"},
            headers=doctor_headers,
        )
        assert response.status_code == 201, response.text
        assert response.json()["filename"] == "resultado.pdf"
        assert response.json()["size_bytes"] > 0

    def test_rejects_disallowed_extension(
        self, client, in_progress_appointment, doctor_headers
    ):
        exam = self._request_exam(client, in_progress_appointment["id"], doctor_headers).json()
        response = client.post(
            f"{API}/exams/{exam['id']}/attachments",
            files={"file": ("malicioso.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
            headers=doctor_headers,
        )
        assert response.status_code == 415

    def test_rejects_empty_file(self, client, in_progress_appointment, doctor_headers):
        exam = self._request_exam(client, in_progress_appointment["id"], doctor_headers).json()
        response = client.post(
            f"{API}/exams/{exam['id']}/attachments",
            files={"file": ("vazio.pdf", io.BytesIO(b""), "application/pdf")},
            headers=doctor_headers,
        )
        assert response.status_code == 422

    def test_filename_is_sanitized(self, client, in_progress_appointment, doctor_headers):
        exam = self._request_exam(client, in_progress_appointment["id"], doctor_headers).json()
        response = client.post(
            f"{API}/exams/{exam['id']}/attachments",
            files={
                "file": (
                    "../../etc/resultado final.pdf",
                    io.BytesIO(b"conteudo"),
                    "application/pdf",
                )
            },
            headers=doctor_headers,
        )
        assert response.status_code == 201
        assert "/" not in response.json()["filename"]

    def test_patient_downloads_own_attachment(
        self, client, in_progress_appointment, doctor_headers, patient_headers
    ):
        exam = self._request_exam(client, in_progress_appointment["id"], doctor_headers).json()
        attachment = client.post(
            f"{API}/exams/{exam['id']}/attachments",
            files={"file": ("resultado.pdf", io.BytesIO(b"conteudo"), "application/pdf")},
            headers=doctor_headers,
        ).json()
        response = client.get(
            f"{API}/exams/attachments/{attachment['id']}/download", headers=patient_headers
        )
        assert response.status_code == 200
        assert response.content == b"conteudo"

    def test_other_patient_cannot_download(
        self, client, in_progress_appointment, doctor_headers
    ):
        exam = self._request_exam(client, in_progress_appointment["id"], doctor_headers).json()
        attachment = client.post(
            f"{API}/exams/{exam['id']}/attachments",
            files={"file": ("resultado.pdf", io.BytesIO(b"conteudo"), "application/pdf")},
            headers=doctor_headers,
        ).json()
        other = auth_headers(client, "paciente2@clinica.com")
        response = client.get(
            f"{API}/exams/attachments/{attachment['id']}/download", headers=other
        )
        assert response.status_code == 403


class TestClinicalHistory:
    def test_history_is_chronological_and_complete(
        self, client, scenario, in_progress_appointment, doctor_headers, patient_headers
    ):
        client.post(
            f"{API}/appointments/{in_progress_appointment['id']}/medical-record",
            json=RECORD_PAYLOAD,
            headers=doctor_headers,
        )
        client.post(
            f"{API}/appointments/{in_progress_appointment['id']}/prescriptions",
            json={
                "medication_name": "Losartana",
                "dosage": "50 mg",
                "frequency": "1x ao dia",
                "duration": "30 dias",
            },
            headers=doctor_headers,
        )
        client.post(
            f"{API}/appointments/{in_progress_appointment['id']}/exams",
            json={"exam_name": "Eletrocardiograma"},
            headers=doctor_headers,
        )

        response = client.get(
            f"{API}/patients/{scenario['patient'].id}/history", headers=patient_headers
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total_appointments"] == 1
        entry = body["entries"][0]
        assert entry["medical_record"]["diagnosis"] == "Angina estavel"
        assert len(entry["prescriptions"]) == 1
        assert len(entry["exams"]) == 1
        assert entry["professional_name"] == "Carlos Souza"

    def test_other_patient_cannot_read_history(self, client, scenario):
        other = auth_headers(client, "paciente2@clinica.com")
        response = client.get(
            f"{API}/patients/{scenario['patient'].id}/history", headers=other
        )
        assert response.status_code == 403

    def test_doctor_can_read_history(self, client, scenario, doctor_headers):
        response = client.get(
            f"{API}/patients/{scenario['patient'].id}/history", headers=doctor_headers
        )
        assert response.status_code == 200

    def test_unknown_patient_returns_404(self, client, doctor_headers):
        response = client.get(f"{API}/patients/9999/history", headers=doctor_headers)
        assert response.status_code == 404
