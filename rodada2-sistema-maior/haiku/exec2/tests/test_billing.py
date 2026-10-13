import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.models import Base
from app.database import get_db
from main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def cleanup():
    yield
    Base.metadata.drop_all(bind=engine)

def create_user(email: str, username: str, role: str, password: str = "SecurePass123!"):
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "username": username,
            "full_name": f"{username.title()} User",
            "role": role,
            "password": password
        }
    )
    return response.json()

def get_auth_token(username: str, password: str = "SecurePass123!"):
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password}
    )
    return response.json()["access_token"]

def test_create_charge():
    create_user("patient@test.com", "patient1", "patient")
    create_user("receptionist@test.com", "receptionist1", "receptionist")

    token = get_auth_token("receptionist1")
    response = client.post(
        "/api/billing/charges",
        json={
            "patient_id": 1,
            "amount": 150.00,
            "appointment_id": None,
            "exam_id": None,
            "payment_method": None,
            "status": "pendente"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["amount"] == 150.00
    assert data["status"] == "pendente"

def test_cannot_pay_already_paid_charge():
    create_user("patient@test.com", "patient1", "patient")
    create_user("receptionist@test.com", "receptionist1", "receptionist")

    token = get_auth_token("receptionist1")

    charge_response = client.post(
        "/api/billing/charges",
        json={
            "patient_id": 1,
            "amount": 150.00,
            "appointment_id": None,
            "exam_id": None,
            "payment_method": None,
            "status": "pendente"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    charge_id = charge_response.json()["id"]

    client.post(
        f"/api/billing/charges/{charge_id}/pay?payment_method=credit_card",
        headers={"Authorization": f"Bearer {token}"}
    )

    response = client.post(
        f"/api/billing/charges/{charge_id}/pay?payment_method=credit_card",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
    assert "already paid" in response.json()["detail"]

def test_get_patient_charges():
    create_user("patient@test.com", "patient1", "patient")
    create_user("receptionist@test.com", "receptionist1", "receptionist")

    token = get_auth_token("receptionist1")

    for i in range(3):
        client.post(
            "/api/billing/charges",
            json={
                "patient_id": 1,
                "amount": 100.00 + i * 10,
                "appointment_id": None,
                "exam_id": None,
                "payment_method": None,
                "status": "pendente"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

    patient_token = get_auth_token("patient1")
    response = client.get(
        "/api/billing/patient/1/charges",
        headers={"Authorization": f"Bearer {patient_token}"}
    )
    assert response.status_code == 200
    charges = response.json()
    assert len(charges) == 3

def test_get_unpaid_charges():
    create_user("patient@test.com", "patient1", "patient")
    create_user("receptionist@test.com", "receptionist1", "receptionist")

    token = get_auth_token("receptionist1")

    charge_response = client.post(
        "/api/billing/charges",
        json={
            "patient_id": 1,
            "amount": 150.00,
            "appointment_id": None,
            "exam_id": None,
            "payment_method": None,
            "status": "pendente"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    charge_id = charge_response.json()["id"]

    client.post(
        f"/api/billing/charges/{charge_id}/pay?payment_method=credit_card",
        headers={"Authorization": f"Bearer {token}"}
    )

    client.post(
        "/api/billing/charges",
        json={
            "patient_id": 1,
            "amount": 200.00,
            "appointment_id": None,
            "exam_id": None,
            "payment_method": None,
            "status": "pendente"
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    patient_token = get_auth_token("patient1")
    response = client.get(
        "/api/billing/patient/1/charges/unpaid",
        headers={"Authorization": f"Bearer {patient_token}"}
    )
    assert response.status_code == 200
    unpaid = response.json()
    assert len(unpaid) == 1
    assert unpaid[0]["amount"] == 200.00

def test_cannot_create_charge_negative_amount():
    create_user("patient@test.com", "patient1", "patient")
    create_user("receptionist@test.com", "receptionist1", "receptionist")

    token = get_auth_token("receptionist1")
    response = client.post(
        "/api/billing/charges",
        json={
            "patient_id": 1,
            "amount": -100.00,
            "appointment_id": None,
            "exam_id": None,
            "payment_method": None,
            "status": "pendente"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
