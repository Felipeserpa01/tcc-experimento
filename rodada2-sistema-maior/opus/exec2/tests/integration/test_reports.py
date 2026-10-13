from datetime import datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.billing import Charge
from app.models.enums import AppointmentStatus as S
from app.models.enums import ChargeStatus, PaymentMethod
from app.models.patient import Patient
from app.models.professional import Professional
from tests.factories import API, make_appointment, make_patient

PERIOD = {"date_from": "2030-01-01", "date_to": "2030-01-31"}


def _charge(db: Session, appointment, amount: str, method: PaymentMethod, status: ChargeStatus, paid_at=None) -> None:
    db.add(
        Charge(
            patient_id=appointment.patient_id,
            appointment_id=appointment.id,
            description="Consulta",
            gross_amount=Decimal(amount),
            discount_percent=Decimal("0"),
            discount_amount=Decimal("0"),
            net_amount=Decimal(amount),
            payment_method=method,
            status=status,
            paid_at=paid_at,
        )
    )
    db.commit()


@pytest.fixture
def dataset(db: Session, patient: Patient, other_patient: Patient, doctor: Professional, doctor2: Professional) -> None:
    third = make_patient(db, full_name="Zeca Frequente")
    a1 = make_appointment(db, patient, doctor, datetime(2030, 1, 2, 9, 0), S.COMPLETED)
    a2 = make_appointment(db, patient, doctor, datetime(2030, 1, 3, 9, 0), S.COMPLETED)
    make_appointment(db, other_patient, doctor, datetime(2030, 1, 3, 10, 0), S.NO_SHOW)
    make_appointment(db, other_patient, doctor, datetime(2030, 1, 4, 10, 0), S.CANCELLED)
    a5 = make_appointment(db, third, doctor2, datetime(2030, 1, 4, 14, 0), S.COMPLETED)
    make_appointment(db, third, doctor2, datetime(2030, 1, 5, 14, 0), S.NO_SHOW)
    make_appointment(db, third, doctor2, datetime(2030, 1, 5, 15, 0), S.NO_SHOW)
    make_appointment(db, patient, doctor2, datetime(2030, 1, 9, 14, 0), S.SCHEDULED)
    make_appointment(db, patient, doctor, datetime(2029, 12, 20, 9, 0), S.COMPLETED)  # fora do período

    _charge(db, a1, "200.00", PaymentMethod.PIX, ChargeStatus.PAID, datetime(2030, 1, 2, 9, 40))
    _charge(db, a2, "200.00", PaymentMethod.CREDIT_CARD, ChargeStatus.PAID, datetime(2030, 1, 3, 9, 40))
    _charge(db, a5, "150.00", PaymentMethod.PIX, ChargeStatus.PAID, datetime(2030, 2, 1, 10, 0))  # pago fora do período
    other = make_appointment(db, patient, doctor2, datetime(2030, 1, 6, 9, 0), S.COMPLETED)
    _charge(db, other, "80.00", PaymentMethod.CASH, ChargeStatus.PENDING)


class TestReports:
    def test_reports_are_admin_only(
        self, client: TestClient, reception_h: dict, doctor_h: dict, patient_h: dict
    ) -> None:
        for headers in (reception_h, doctor_h, patient_h):
            assert client.get(f"{API}/reports/revenue", headers=headers).status_code == 403

    def test_by_status_includes_all_statuses(self, client: TestClient, admin_h: dict, dataset: None) -> None:
        body = client.get(f"{API}/reports/appointments/by-status", params=PERIOD, headers=admin_h).json()
        totals = {item["status"]: item["total"] for item in body["items"]}
        assert totals == {
            "agendada": 1,
            "confirmada": 0,
            "em_andamento": 0,
            "realizada": 4,
            "cancelada": 1,
            "faltou": 3,
        }
        assert body["total"] == 9

    def test_by_professional(
        self, client: TestClient, admin_h: dict, dataset: None, doctor: Professional, doctor2: Professional
    ) -> None:
        body = client.get(f"{API}/reports/appointments/by-professional", params=PERIOD, headers=admin_h).json()
        rows = {row["professional_id"]: row for row in body["items"]}
        assert rows[doctor.id]["total"] == 4
        assert rows[doctor.id]["completed"] == 2
        assert rows[doctor.id]["cancelled"] == 1
        assert rows[doctor2.id]["no_show"] == 2
        filtered = client.get(
            f"{API}/reports/appointments/by-professional",
            params={**PERIOD, "specialty": "dermatologia"},
            headers=admin_h,
        ).json()
        assert [r["professional_id"] for r in filtered["items"]] == [doctor2.id]

    def test_by_specialty(self, client: TestClient, admin_h: dict, dataset: None) -> None:
        body = client.get(f"{API}/reports/appointments/by-specialty", params=PERIOD, headers=admin_h).json()
        assert {r["specialty"]: r["total"] for r in body["items"]} == {"Cardiologia": 4, "Dermatologia": 5}

    def test_by_period(self, client: TestClient, admin_h: dict, dataset: None) -> None:
        daily = client.get(f"{API}/reports/appointments/by-period", params=PERIOD, headers=admin_h).json()
        assert {i["period"]: i["total"] for i in daily["items"]}["2030-01-03"] == 2
        monthly = client.get(
            f"{API}/reports/appointments/by-period",
            params={"date_from": "2029-12-01", "date_to": "2030-01-31", "granularity": "month", "status": "realizada"},
            headers=admin_h,
        ).json()
        assert monthly["items"] == [{"period": "2029-12", "total": 1}, {"period": "2030-01", "total": 4}]

    def test_revenue(self, client: TestClient, admin_h: dict, dataset: None) -> None:
        body = client.get(f"{API}/reports/revenue", params=PERIOD, headers=admin_h).json()
        assert body["total_received"] == "400.00"
        assert body["paid_count"] == 2
        assert body["pending_total"] == "80.00"
        assert {m["payment_method"]: m["total"] for m in body["by_payment_method"]} == {
            "pix": "200.00",
            "cartao_credito": "200.00",
        }
        assert [p["period"] for p in body["by_period"]] == ["2030-01-02", "2030-01-03"]

    def test_no_show_rate(
        self, client: TestClient, admin_h: dict, dataset: None, doctor: Professional, doctor2: Professional
    ) -> None:
        body = client.get(f"{API}/reports/no-show-rate", params=PERIOD, headers=admin_h).json()
        rates = {r["professional_id"]: r["no_show_rate"] for r in body["items"]}
        assert rates[doctor2.id] == "50.00"  # 2 faltas / (2 realizadas + 2 faltas)
        assert rates[doctor.id] == "33.33"  # 1 / (2 + 1)
        assert body["items"][0]["professional_id"] == doctor2.id
        assert body["overall_rate"] == "42.86"  # 3 / 7

    def test_top_patients(self, client: TestClient, admin_h: dict, dataset: None, patient: Patient) -> None:
        body = client.get(f"{API}/reports/top-patients", params={**PERIOD, "limit": 2}, headers=admin_h).json()
        assert body["items"][0] == {"patient_id": patient.id, "patient_name": "Maria da Silva", "total_appointments": 3}
        assert len(body["items"]) == 2

    def test_default_period_and_validation(self, client: TestClient, admin_h: dict) -> None:
        default = client.get(f"{API}/reports/appointments/by-status", headers=admin_h).json()
        assert default["period"] == {"date_from": "2029-12-09", "date_to": "2030-01-07"}
        invalid = client.get(
            f"{API}/reports/revenue", params={"date_from": "2030-02-01", "date_to": "2030-01-01"}, headers=admin_h
        )
        assert invalid.status_code == 422
        bad_granularity = client.get(f"{API}/reports/revenue", params={"granularity": "year"}, headers=admin_h)
        assert bad_granularity.status_code == 422

    def test_empty_reports(self, client: TestClient, admin_h: dict) -> None:
        revenue = client.get(f"{API}/reports/revenue", params=PERIOD, headers=admin_h).json()
        assert revenue["total_received"] == "0.00"
        assert revenue["by_payment_method"] == []
        no_show = client.get(f"{API}/reports/no-show-rate", params=PERIOD, headers=admin_h).json()
        assert no_show["overall_rate"] == "0.00"
