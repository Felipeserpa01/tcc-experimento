import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.models import Base, User, UserRole, Patient, Professional, AvailabilitySchedule
from app.database import get_db
from main import app
import os

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

def test_cannot_schedule_in_past():
    create_user("patient@test.com", "patient1", "patient")
    create_user("doctor@test.com", "doctor1", "doctor")

    patient_id = 1
    professional_id = 2
    past_date = (datetime.utcnow() - timedelta(days=1)).isoformat()

    token = get_auth_token("patient1")
    response = client.post(
        "/api/appointments/",
        json={
            "patient_id": patient_id,
            "professional_id": professional_id,
            "appointment_date": past_date
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
    assert "Cannot schedule in the past" in response.json()["detail"]

def test_cannot_schedule_outside_availability():
    create_user("patient@test.com", "patient1", "patient")
    create_user("doctor@test.com", "doctor1", "doctor")

    db = TestingSessionLocal()
    patient = db.query(Patient).first()
    professional = db.query(Professional).first()

    future_date = datetime.utcnow() + timedelta(days=7)
    future_date = future_date.replace(hour=22, minute=0)

    token = get_auth_token("patient1")
    response = client.post(
        "/api/appointments/",
        json={
            "patient_id": patient.id,
            "professional_id": professional.id,
            "appointment_date": future_date.isoformat()
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
    db.close()

def test_conflict_handling():
    create_user("patient1@test.com", "patient1", "patient")
    create_user("patient2@test.com", "patient2", "patient")
    create_user("doctor@test.com", "doctor1", "doctor")

    db = TestingSessionLocal()
    doctor = db.query(Professional).first()

    schedule = AvailabilitySchedule(
        professional_id=doctor.id,
        day_of_week=0,
        start_time=datetime.now().time().replace(hour=9, minute=0),
        end_time=datetime.now().time().replace(hour=17, minute=0)
    )
    db.add(schedule)
    db.commit()

    future_monday = datetime.utcnow() + timedelta(days=(7-datetime.utcnow().weekday()))
    future_monday = future_monday.replace(hour=10, minute=0, second=0, microsecond=0)

    token1 = get_auth_token("patient1")
    response1 = client.post(
        "/api/appointments/",
        json={
            "patient_id": 1,
            "professional_id": doctor.id,
            "appointment_date": future_monday.isoformat()
        },
        headers={"Authorization": f"Bearer {token1}"}
    )
    assert response1.status_code == 200

    token2 = get_auth_token("patient2")
    response2 = client.post(
        "/api/appointments/",
        json={
            "patient_id": 2,
            "professional_id": doctor.id,
            "appointment_date": future_monday.isoformat()
        },
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert response2.status_code == 200
    data = response2.json()
    assert "waiting_list" in data.get("message", "").lower() or "position" in data

    db.close()

def test_cancel_appointment():
    create_user("patient@test.com", "patient1", "patient")
    create_user("doctor@test.com", "doctor1", "doctor")

    db = TestingSessionLocal()
    doctor = db.query(Professional).first()

    schedule = AvailabilitySchedule(
        professional_id=doctor.id,
        day_of_week=0,
        start_time=datetime.now().time().replace(hour=9, minute=0),
        end_time=datetime.now().time().replace(hour=17, minute=0)
    )
    db.add(schedule)
    db.commit()

    future_monday = datetime.utcnow() + timedelta(days=(7-datetime.utcnow().weekday()))
    future_monday = future_monday.replace(hour=10, minute=0, second=0, microsecond=0)

    token = get_auth_token("patient1")
    appt_response = client.post(
        "/api/appointments/",
        json={
            "patient_id": 1,
            "professional_id": doctor.id,
            "appointment_date": future_monday.isoformat()
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    appt_id = appt_response.json()["id"]

    doctor_token = get_auth_token("doctor1")
    response = client.post(
        f"/api/appointments/{appt_id}/cancel?reason=Doctor%20unavailable",
        headers={"Authorization": f"Bearer {doctor_token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "cancelada"

    db.close()

def test_confirm_appointment():
    create_user("patient@test.com", "patient1", "patient")
    create_user("doctor@test.com", "doctor1", "doctor")

    db = TestingSessionLocal()
    doctor = db.query(Professional).first()

    schedule = AvailabilitySchedule(
        professional_id=doctor.id,
        day_of_week=0,
        start_time=datetime.now().time().replace(hour=9, minute=0),
        end_time=datetime.now().time().replace(hour=17, minute=0)
    )
    db.add(schedule)
    db.commit()

    future_monday = datetime.utcnow() + timedelta(days=(7-datetime.utcnow().weekday()))
    future_monday = future_monday.replace(hour=10, minute=0, second=0, microsecond=0)

    token = get_auth_token("patient1")
    appt_response = client.post(
        "/api/appointments/",
        json={
            "patient_id": 1,
            "professional_id": doctor.id,
            "appointment_date": future_monday.isoformat()
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    appt_id = appt_response.json()["id"]

    doctor_token = get_auth_token("doctor1")
    response = client.post(
        f"/api/appointments/{appt_id}/confirm",
        headers={"Authorization": f"Bearer {doctor_token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "confirmada"

    db.close()
