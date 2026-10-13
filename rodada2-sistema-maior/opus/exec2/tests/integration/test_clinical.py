from datetime import datetime
from typing import ClassVar

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.enums import AppointmentStatus
from app.models.patient import Patient
from app.models.professional import Professional
from tests.factories import API, make_appointment

RECORD = {
    "chief_complaint": "Dor no peito ao esforço",
    "diagnosis": "Angina estável",
    "icd10_code": "i209",
    "notes": "Solicitar teste ergométrico.",
}
PDF_BYTES = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


@pytest.fixture
def attended(db: Session, patient: Patient, doctor: Professional) -> int:
    """Consulta de hoje, já em andamento com o médico responsável."""
    return make_appointment(db, patient, doctor, datetime(2030, 1, 7, 8, 0), status=AppointmentStatus.IN_PROGRESS).id


@pytest.fixture
def scheduled(db: Session, patient: Patient, doctor: Professional) -> int:
    return make_appointment(db, patient, doctor, datetime(2030, 1, 8, 9, 0)).id


class TestMedicalRecord:
    def test_responsible_doctor_registers_record(self, client: TestClient, doctor_h: dict, attended: int) -> None:
        response = client.post(f"{API}/appointments/{attended}/medical-record", json=RECORD, headers=doctor_h)
        assert response.status_code == 201, response.text
        assert response.json()["icd10_code"] == "I20.9"
        assert response.json()["professional_name"] == "Carlos Andrade"

    def test_duplicate_record(self, client: TestClient, doctor_h: dict, attended: int) -> None:
        client.post(f"{API}/appointments/{attended}/medical-record", json=RECORD, headers=doctor_h)
        response = client.post(f"{API}/appointments/{attended}/medical-record", json=RECORD, headers=doctor_h)
        assert response.status_code == 409

    def test_record_requires_attended_appointment(self, client: TestClient, doctor_h: dict, scheduled: int) -> None:
        response = client.post(f"{API}/appointments/{scheduled}/medical-record", json=RECORD, headers=doctor_h)
        assert response.status_code == 422
        assert response.json()["error"]["details"]["status_atual"] == "agendada"

    @pytest.mark.parametrize("headers_fixture", ["doctor2_h", "nurse_h", "reception_h", "admin_h", "patient_h"])
    def test_only_responsible_doctor_writes(
        self, client: TestClient, request: pytest.FixtureRequest, attended: int, headers_fixture: str
    ) -> None:
        headers = request.getfixturevalue(headers_fixture)
        response = client.post(f"{API}/appointments/{attended}/medical-record", json=RECORD, headers=headers)
        assert response.status_code == 403

    def test_update_record(self, client: TestClient, doctor_h: dict, doctor2_h: dict, attended: int) -> None:
        url = f"{API}/appointments/{attended}/medical-record"
        assert client.patch(url, json={"notes": "x"}, headers=doctor_h).status_code == 404
        client.post(url, json=RECORD, headers=doctor_h)
        response = client.patch(url, json={"diagnosis": "Angina instável"}, headers=doctor_h)
        assert response.status_code == 200 and response.json()["diagnosis"] == "Angina instável"
        assert client.patch(url, json={"diagnosis": "Outro"}, headers=doctor2_h).status_code == 403
        assert client.patch(url, json={"diagnosis": None}, headers=doctor_h).status_code == 422

    def test_patient_reads_own_record_but_cannot_edit(
        self, client: TestClient, doctor_h: dict, patient_h: dict, other_patient_h: dict, attended: int
    ) -> None:
        url = f"{API}/appointments/{attended}/medical-record"
        client.post(url, json=RECORD, headers=doctor_h)
        assert client.get(url, headers=patient_h).status_code == 200
        assert client.patch(url, json={"notes": "editado"}, headers=patient_h).status_code == 403
        assert client.get(url, headers=other_patient_h).status_code == 403

    def test_front_desk_cannot_read_clinical_data(
        self, client: TestClient, doctor_h: dict, reception_h: dict, nurse_h: dict, attended: int
    ) -> None:
        url = f"{API}/appointments/{attended}/medical-record"
        client.post(url, json=RECORD, headers=doctor_h)
        assert client.get(url, headers=reception_h).status_code == 403
        assert client.get(url, headers=nurse_h).status_code == 200

    def test_viewing_record_is_audited(
        self, client: TestClient, doctor_h: dict, patient_h: dict, attended: int, db: Session, patient: Patient
    ) -> None:
        url = f"{API}/appointments/{attended}/medical-record"
        client.post(url, json=RECORD, headers=doctor_h)
        client.get(url, headers=patient_h)
        viewer_ids = db.scalars(select(AuditLog.user_id).where(AuditLog.action == "prontuario.visualizado")).all()
        assert viewer_ids == [patient.user_id]


class TestPrescriptions:
    ITEMS: ClassVar[dict] = {
        "items": [
            {"medication_name": "AAS", "dosage": "100 mg", "frequency": "1x ao dia", "duration": "contínuo"},
            {
                "medication_name": "Atenolol",
                "dosage": "25 mg",
                "frequency": "12/12h",
                "duration": "30 dias",
                "instructions": "Tomar após as refeições",
            },
        ]
    }

    def test_register_and_list(self, client: TestClient, doctor_h: dict, patient_h: dict, attended: int) -> None:
        response = client.post(f"{API}/appointments/{attended}/prescriptions", json=self.ITEMS, headers=doctor_h)
        assert response.status_code == 201
        assert [p["medication_name"] for p in response.json()] == ["AAS", "Atenolol"]
        listed = client.get(f"{API}/appointments/{attended}/prescriptions", headers=patient_h)
        assert len(listed.json()) == 2

    def test_validation(self, client: TestClient, doctor_h: dict, attended: int) -> None:
        url = f"{API}/appointments/{attended}/prescriptions"
        assert client.post(url, json={"items": []}, headers=doctor_h).status_code == 422
        incomplete = {"items": [{"medication_name": "AAS", "dosage": "100 mg"}]}
        response = client.post(url, json=incomplete, headers=doctor_h)
        assert response.status_code == 422
        assert {d["field"] for d in response.json()["error"]["details"]} == {"items.0.frequency", "items.0.duration"}

    def test_other_doctor_and_patient_cannot_prescribe(
        self, client: TestClient, doctor2_h: dict, patient_h: dict, attended: int
    ) -> None:
        url = f"{API}/appointments/{attended}/prescriptions"
        assert client.post(url, json=self.ITEMS, headers=doctor2_h).status_code == 403
        assert client.post(url, json=self.ITEMS, headers=patient_h).status_code == 403


class TestExams:
    @pytest.fixture
    def exam_id(self, client: TestClient, doctor_h: dict, attended: int) -> int:
        response = client.post(
            f"{API}/appointments/{attended}/exams",
            json={"exams": [{"exam_name": "Teste ergométrico", "clinical_indication": "Dor torácica"}]},
            headers=doctor_h,
        )
        assert response.status_code == 201
        assert response.json()[0]["status"] == "solicitado"
        return response.json()[0]["id"]

    def test_attach_text_result(self, client: TestClient, doctor_h: dict, patient_h: dict, exam_id: int) -> None:
        response = client.post(
            f"{API}/exams/{exam_id}/result", data={"result_text": "Sem alterações"}, headers=doctor_h
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "resultado_disponivel"
        assert body["has_result_file"] is False
        assert client.get(f"{API}/exams/{exam_id}", headers=patient_h).json()["result_text"] == "Sem alterações"

    def test_attach_and_download_file(self, client: TestClient, doctor_h: dict, patient_h: dict, exam_id: int) -> None:
        response = client.post(
            f"{API}/exams/{exam_id}/result",
            files={"file": ("../../laudo final.pdf", PDF_BYTES, "application/pdf")},
            headers=doctor_h,
        )
        assert response.status_code == 200, response.text
        assert response.json()["result_file_name"] == "laudo final.pdf"
        download = client.get(f"{API}/exams/{exam_id}/result-file", headers=patient_h)
        assert download.status_code == 200
        assert download.content == PDF_BYTES
        assert download.headers["content-type"] == "application/pdf"

    def test_rejects_unsupported_or_spoofed_files(self, client: TestClient, doctor_h: dict, exam_id: int) -> None:
        url = f"{API}/exams/{exam_id}/result"
        exe = client.post(url, files={"file": ("virus.exe", b"MZ...", "application/octet-stream")}, headers=doctor_h)
        assert exe.status_code == 415
        spoofed = client.post(url, files={"file": ("laudo.pdf", b"not a pdf", "application/pdf")}, headers=doctor_h)
        assert spoofed.status_code == 415
        empty = client.post(url, data={}, headers=doctor_h)
        assert empty.status_code == 422

    def test_result_can_only_be_registered_once(self, client: TestClient, doctor_h: dict, exam_id: int) -> None:
        url = f"{API}/exams/{exam_id}/result"
        client.post(url, data={"result_text": "Normal"}, headers=doctor_h)
        assert client.post(url, data={"result_text": "Outro"}, headers=doctor_h).status_code == 409

    def test_only_responsible_doctor_attaches(
        self, client: TestClient, doctor2_h: dict, nurse_h: dict, exam_id: int
    ) -> None:
        url = f"{API}/exams/{exam_id}/result"
        assert client.post(url, data={"result_text": "Normal"}, headers=doctor2_h).status_code == 403
        assert client.post(url, data={"result_text": "Normal"}, headers=nurse_h).status_code == 403

    def test_cancel_exam(self, client: TestClient, doctor_h: dict, exam_id: int) -> None:
        response = client.post(f"{API}/exams/{exam_id}/cancel", headers=doctor_h)
        assert response.status_code == 200 and response.json()["status"] == "cancelado"
        assert (
            client.post(f"{API}/exams/{exam_id}/result", data={"result_text": "x"}, headers=doctor_h).status_code == 422
        )
        assert client.post(f"{API}/exams/{exam_id}/cancel", headers=doctor_h).status_code == 422

    def test_download_without_file(self, client: TestClient, doctor_h: dict, exam_id: int) -> None:
        assert client.get(f"{API}/exams/{exam_id}/result-file", headers=doctor_h).status_code == 404

    def test_other_patient_cannot_see_exam(self, client: TestClient, other_patient_h: dict, exam_id: int) -> None:
        assert client.get(f"{API}/exams/{exam_id}", headers=other_patient_h).status_code == 403


class TestClinicalHistory:
    def test_history_is_chronological_and_complete(
        self,
        client: TestClient,
        db: Session,
        doctor_h: dict,
        patient_h: dict,
        patient: Patient,
        doctor: Professional,
        doctor2: Professional,
        attended: int,
    ) -> None:
        older = make_appointment(db, patient, doctor2, datetime(2029, 12, 1, 14, 0), status=AppointmentStatus.COMPLETED)
        client.post(f"{API}/appointments/{attended}/medical-record", json=RECORD, headers=doctor_h)
        client.post(f"{API}/appointments/{attended}/prescriptions", json=TestPrescriptions.ITEMS, headers=doctor_h)
        client.post(f"{API}/appointments/{attended}/exams", json={"exams": [{"exam_name": "ECG"}]}, headers=doctor_h)

        response = client.get(f"{API}/patients/{patient.id}/clinical-history", headers=patient_h)
        assert response.status_code == 200
        body = response.json()
        assert [e["appointment_id"] for e in body["entries"]] == [older.id, attended]
        assert body["total_appointments"] == 2
        assert body["total_prescriptions"] == 2
        assert body["total_exams"] == 1
        latest = body["entries"][1]
        assert latest["medical_record"]["diagnosis"] == "Angina estável"
        assert body["entries"][0]["medical_record"] is None

        filtered = client.get(
            f"{API}/patients/{patient.id}/clinical-history", params={"date_from": "2030-01-01"}, headers=doctor_h
        )
        assert filtered.json()["total_appointments"] == 1

    def test_history_access_rules(
        self, client: TestClient, patient: Patient, other_patient_h: dict, reception_h: dict, nurse_h: dict
    ) -> None:
        url = f"{API}/patients/{patient.id}/clinical-history"
        assert client.get(url, headers=other_patient_h).status_code == 403
        assert client.get(url, headers=reception_h).status_code == 403
        assert client.get(url, headers=nurse_h).status_code == 200
