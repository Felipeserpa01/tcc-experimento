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

def test_create_patient():
    create_user("patient@test.com", "patient1", "patient")
    create_user("receptionist@test.com", "receptionist1", "receptionist")

    token = get_auth_token("receptionist1")
    response = client.post(
        "/api/patients/",
        json={
            "user_id": 1,
            "cpf": "12345678901",
            "date_of_birth": "1990-01-15",
            "sex": "M",
            "phone": "11999999999",
            "address": "Rua Test, 123",
            "city": "São Paulo",
            "state": "SP",
            "zip_code": "01234-567",
            "insurance_plan": "Unimed",
            "allergies": "Penicilina",
            "observations": "Sem observações"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["cpf"] == "12345678901"

def test_invalid_cpf():
    create_user("patient@test.com", "patient1", "patient")
    create_user("receptionist@test.com", "receptionist1", "receptionist")

    token = get_auth_token("receptionist1")
    response = client.post(
        "/api/patients/",
        json={
            "user_id": 1,
            "cpf": "00000000000",
            "date_of_birth": "1990-01-15",
            "sex": "M",
            "phone": "11999999999",
            "address": "Rua Test, 123",
            "city": "São Paulo",
            "state": "SP",
            "zip_code": "01234-567",
            "insurance_plan": None,
            "allergies": None,
            "observations": None
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
    assert "Invalid CPF" in response.json()["detail"]

def test_duplicate_cpf():
    create_user("patient1@test.com", "patient1", "patient")
    create_user("patient2@test.com", "patient2", "patient")
    create_user("receptionist@test.com", "receptionist1", "receptionist")

    token = get_auth_token("receptionist1")

    client.post(
        "/api/patients/",
        json={
            "user_id": 1,
            "cpf": "12345678901",
            "date_of_birth": "1990-01-15",
            "sex": "M",
            "phone": "11999999999",
            "address": "Rua Test, 123",
            "city": "São Paulo",
            "state": "SP",
            "zip_code": "01234-567",
            "insurance_plan": "Unimed",
            "allergies": "Penicilina",
            "observations": "Sem observações"
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    response = client.post(
        "/api/patients/",
        json={
            "user_id": 2,
            "cpf": "12345678901",
            "date_of_birth": "1985-05-20",
            "sex": "F",
            "phone": "11988888888",
            "address": "Rua Test 2, 456",
            "city": "São Paulo",
            "state": "SP",
            "zip_code": "01234-568",
            "insurance_plan": "Bradesco",
            "allergies": None,
            "observations": None
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]

def test_patient_access_control():
    create_user("patient1@test.com", "patient1", "patient")
    create_user("patient2@test.com", "patient2", "patient")
    create_user("receptionist@test.com", "receptionist1", "receptionist")

    token = get_auth_token("receptionist1")

    client.post(
        "/api/patients/",
        json={
            "user_id": 1,
            "cpf": "12345678901",
            "date_of_birth": "1990-01-15",
            "sex": "M",
            "phone": "11999999999",
            "address": "Rua Test, 123",
            "city": "São Paulo",
            "state": "SP",
            "zip_code": "01234-567",
            "insurance_plan": "Unimed",
            "allergies": "Penicilina",
            "observations": "Sem observações"
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    patient1_token = get_auth_token("patient1")
    patient2_token = get_auth_token("patient2")

    response = client.get(
        "/api/patients/1",
        headers={"Authorization": f"Bearer {patient1_token}"}
    )
    assert response.status_code == 200

    response = client.get(
        "/api/patients/1",
        headers={"Authorization": f"Bearer {patient2_token}"}
    )
    assert response.status_code == 403

def test_update_patient():
    create_user("patient@test.com", "patient1", "patient")
    create_user("receptionist@test.com", "receptionist1", "receptionist")

    token = get_auth_token("receptionist1")

    client.post(
        "/api/patients/",
        json={
            "user_id": 1,
            "cpf": "12345678901",
            "date_of_birth": "1990-01-15",
            "sex": "M",
            "phone": "11999999999",
            "address": "Rua Test, 123",
            "city": "São Paulo",
            "state": "SP",
            "zip_code": "01234-567",
            "insurance_plan": "Unimed",
            "allergies": "Penicilina",
            "observations": "Sem observações"
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    response = client.put(
        "/api/patients/1",
        json={
            "phone": "11988888888",
            "address": "Rua Test 2, 456"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["phone"] == "11988888888"
    assert data["address"] == "Rua Test 2, 456"

def test_list_patients():
    create_user("receptionist@test.com", "receptionist1", "receptionist")
    create_user("patient1@test.com", "patient1", "patient")
    create_user("patient2@test.com", "patient2", "patient")

    token = get_auth_token("receptionist1")

    for i, cpf in enumerate(["12345678901", "98765432101"]):
        client.post(
            "/api/patients/",
            json={
                "user_id": i + 2,
                "cpf": cpf,
                "date_of_birth": "1990-01-15",
                "sex": "M",
                "phone": "11999999999",
                "address": "Rua Test, 123",
                "city": "São Paulo",
                "state": "SP",
                "zip_code": "01234-567",
                "insurance_plan": "Unimed",
                "allergies": None,
                "observations": None
            },
            headers={"Authorization": f"Bearer {token}"}
        )

    response = client.get(
        "/api/patients/",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    patients = response.json()
    assert len(patients) == 2
