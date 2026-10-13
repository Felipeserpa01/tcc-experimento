"""Integration tests for registration, login, account lockout and password flows."""
from app.core.enums import UserRole
from app.core.security import hash_reset_token
from app.models.user import User
from tests.conftest import VALID_PASSWORD, create_user


def test_register_patient_succeeds(client):
    resp = client.post(
        "/auth/register",
        json={"email": "novo.paciente@clinica.com", "password": VALID_PASSWORD, "role": "paciente"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["role"] == "paciente"


def test_register_rejects_weak_password(client):
    resp = client.post(
        "/auth/register",
        json={"email": "fraco@clinica.com", "password": "12345678", "role": "paciente"},
    )
    assert resp.status_code == 422


def test_register_rejects_non_patient_roles(client):
    resp = client.post(
        "/auth/register",
        json={"email": "medico@clinica.com", "password": VALID_PASSWORD, "role": "medico"},
    )
    assert resp.status_code == 422
    assert "paciente" in resp.json()["detail"].lower()


def test_register_rejects_duplicate_email(client):
    payload = {"email": "duplicado@clinica.com", "password": VALID_PASSWORD, "role": "paciente"}
    first = client.post("/auth/register", json=payload)
    assert first.status_code == 201
    second = client.post("/auth/register", json=payload)
    assert second.status_code == 409


def test_login_success_returns_tokens(client, db_session):
    create_user(db_session, "login@clinica.com", UserRole.PACIENTE)
    resp = client.post("/auth/login", json={"email": "login@clinica.com", "password": VALID_PASSWORD})
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body and "refresh_token" in body


def test_login_wrong_password_fails(client, db_session):
    create_user(db_session, "wrongpass@clinica.com", UserRole.PACIENTE)
    resp = client.post(
        "/auth/login", json={"email": "wrongpass@clinica.com", "password": "SenhaErrada999!"}
    )
    assert resp.status_code == 401


def test_login_nonexistent_user_fails(client):
    resp = client.post("/auth/login", json={"email": "naoexiste@clinica.com", "password": VALID_PASSWORD})
    assert resp.status_code == 401


def test_account_locks_after_five_failed_attempts(client, db_session):
    create_user(db_session, "lockout@clinica.com", UserRole.PACIENTE)
    for _ in range(5):
        resp = client.post(
            "/auth/login", json={"email": "lockout@clinica.com", "password": "SenhaErrada999!"}
        )
        assert resp.status_code == 401

    # Sixth attempt, even with the correct password, must be blocked while locked.
    resp = client.post("/auth/login", json={"email": "lockout@clinica.com", "password": VALID_PASSWORD})
    assert resp.status_code == 423


def test_failed_attempts_reset_after_successful_login(client, db_session):
    create_user(db_session, "reset@clinica.com", UserRole.PACIENTE)
    for _ in range(3):
        client.post("/auth/login", json={"email": "reset@clinica.com", "password": "SenhaErrada999!"})

    ok = client.post("/auth/login", json={"email": "reset@clinica.com", "password": VALID_PASSWORD})
    assert ok.status_code == 200

    db_session.expire_all()
    user = db_session.query(User).filter(User.email == "reset@clinica.com").first()
    assert user.failed_login_attempts == 0


def test_refresh_token_issues_new_access_token(client, db_session):
    create_user(db_session, "refresh@clinica.com", UserRole.PACIENTE)
    login = client.post("/auth/login", json={"email": "refresh@clinica.com", "password": VALID_PASSWORD})
    refresh_token = login.json()["refresh_token"]

    resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_refresh_rejects_access_token_used_as_refresh(client, db_session):
    create_user(db_session, "wrongtype@clinica.com", UserRole.PACIENTE)
    login = client.post("/auth/login", json={"email": "wrongtype@clinica.com", "password": VALID_PASSWORD})
    access_token = login.json()["access_token"]

    resp = client.post("/auth/refresh", json={"refresh_token": access_token})
    assert resp.status_code == 401


def test_me_requires_authentication(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user(client, db_session):
    create_user(db_session, "me@clinica.com", UserRole.PACIENTE)
    login = client.post("/auth/login", json={"email": "me@clinica.com", "password": VALID_PASSWORD})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = client.get("/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@clinica.com"


def test_change_password_requires_current_password(client, db_session):
    create_user(db_session, "changepw@clinica.com", UserRole.PACIENTE)
    login = client.post("/auth/login", json={"email": "changepw@clinica.com", "password": VALID_PASSWORD})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    wrong = client.post(
        "/auth/change-password",
        json={"current_password": "SenhaErrada999!", "new_password": "NovaSenha456!"},
        headers=headers,
    )
    assert wrong.status_code == 401

    right = client.post(
        "/auth/change-password",
        json={"current_password": VALID_PASSWORD, "new_password": "NovaSenha456!"},
        headers=headers,
    )
    assert right.status_code == 200

    relogin = client.post(
        "/auth/login", json={"email": "changepw@clinica.com", "password": "NovaSenha456!"}
    )
    assert relogin.status_code == 200


def test_forgot_password_does_not_leak_account_existence(client):
    exists_resp = client.post("/auth/forgot-password", json={"email": "naoexiste@clinica.com"})
    assert exists_resp.status_code == 200
    assert "instruções" in exists_resp.json()["message"].lower()


def test_reset_password_full_flow(client, db_session):
    from app.services.auth_service import AuthService

    create_user(db_session, "forgot@clinica.com", UserRole.PACIENTE)
    service = AuthService(db_session)
    plain_token = service.request_password_reset("forgot@clinica.com")
    assert plain_token is not None

    resp = client.post(
        "/auth/reset-password", json={"token": plain_token, "new_password": "SenhaResetada789!"}
    )
    assert resp.status_code == 200

    login = client.post(
        "/auth/login", json={"email": "forgot@clinica.com", "password": "SenhaResetada789!"}
    )
    assert login.status_code == 200


def test_reset_password_rejects_invalid_token(client):
    resp = client.post(
        "/auth/reset-password", json={"token": "token-invalido", "new_password": "SenhaResetada789!"}
    )
    assert resp.status_code == 404


def test_reset_token_is_hashed_at_rest(client, db_session):
    from app.services.auth_service import AuthService

    create_user(db_session, "hashcheck@clinica.com", UserRole.PACIENTE)
    service = AuthService(db_session)
    plain_token = service.request_password_reset("hashcheck@clinica.com")

    db_session.expire_all()
    user = db_session.query(User).filter(User.email == "hashcheck@clinica.com").first()
    assert user.reset_token != plain_token
    assert user.reset_token == hash_reset_token(plain_token)
