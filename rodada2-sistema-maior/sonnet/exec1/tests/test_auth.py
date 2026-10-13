from tests.conftest import auth_header

VALID_REGISTER_PAYLOAD = {
    "email": "novo.paciente@clinica.com",
    "password": "Senha123!",
    "full_name": "Maria Oliveira",
    "cpf": "529.982.247-25",
    "birth_date": "1995-05-20",
    "sex": "F",
    "phone": "11988887777",
    "address_street": "Rua das Flores",
    "address_number": "50",
    "address_neighborhood": "Jardim",
    "address_city": "São Paulo",
    "address_state": "SP",
    "address_zip_code": "01001-000",
}


def test_register_patient_success(client):
    response = client.post("/auth/register", json=VALID_REGISTER_PAYLOAD)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == VALID_REGISTER_PAYLOAD["email"]
    assert body["role"] == "paciente"


def test_register_rejects_weak_password(client):
    payload = dict(VALID_REGISTER_PAYLOAD, password="123")
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 422


def test_register_rejects_invalid_cpf(client):
    payload = dict(VALID_REGISTER_PAYLOAD, cpf="111.111.111-11")
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 422


def test_register_rejects_duplicate_email(client):
    client.post("/auth/register", json=VALID_REGISTER_PAYLOAD)
    response = client.post("/auth/register", json=VALID_REGISTER_PAYLOAD)
    assert response.status_code == 409


def test_login_success(client):
    client.post("/auth/register", json=VALID_REGISTER_PAYLOAD)
    response = client.post(
        "/auth/login", json={"email": VALID_REGISTER_PAYLOAD["email"], "password": "Senha123!"}
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body


def test_login_with_wrong_password_fails(client):
    client.post("/auth/register", json=VALID_REGISTER_PAYLOAD)
    response = client.post(
        "/auth/login", json={"email": VALID_REGISTER_PAYLOAD["email"], "password": "SenhaErrada1!"}
    )
    assert response.status_code == 401


def test_account_locks_after_five_failed_attempts(client):
    client.post("/auth/register", json=VALID_REGISTER_PAYLOAD)
    for _ in range(5):
        client.post(
            "/auth/login", json={"email": VALID_REGISTER_PAYLOAD["email"], "password": "SenhaErrada1!"}
        )

    response = client.post(
        "/auth/login", json={"email": VALID_REGISTER_PAYLOAD["email"], "password": "Senha123!"}
    )
    assert response.status_code == 423


def test_refresh_token_issues_new_access_token(client):
    client.post("/auth/register", json=VALID_REGISTER_PAYLOAD)
    login_response = client.post(
        "/auth/login", json={"email": VALID_REGISTER_PAYLOAD["email"], "password": "Senha123!"}
    )
    refresh_token = login_response.json()["refresh_token"]

    response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_logout_revokes_refresh_token(client):
    client.post("/auth/register", json=VALID_REGISTER_PAYLOAD)
    login_response = client.post(
        "/auth/login", json={"email": VALID_REGISTER_PAYLOAD["email"], "password": "Senha123!"}
    )
    refresh_token = login_response.json()["refresh_token"]

    logout_response = client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert logout_response.status_code == 204

    refresh_response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_response.status_code == 401


def test_change_password_success(client):
    client.post("/auth/register", json=VALID_REGISTER_PAYLOAD)
    login_response = client.post(
        "/auth/login", json={"email": VALID_REGISTER_PAYLOAD["email"], "password": "Senha123!"}
    )
    token = login_response.json()["access_token"]

    response = client.post(
        "/auth/change-password",
        json={"current_password": "Senha123!", "new_password": "NovaSenha456!"},
        headers=auth_header(token),
    )
    assert response.status_code == 204

    new_login = client.post(
        "/auth/login", json={"email": VALID_REGISTER_PAYLOAD["email"], "password": "NovaSenha456!"}
    )
    assert new_login.status_code == 200


def test_forgot_and_reset_password_flow(client):
    client.post("/auth/register", json=VALID_REGISTER_PAYLOAD)

    forgot_response = client.post(
        "/auth/forgot-password", json={"email": VALID_REGISTER_PAYLOAD["email"]}
    )
    assert forgot_response.status_code == 200
    reset_token = forgot_response.json()["reset_token"]
    assert reset_token is not None

    reset_response = client.post(
        "/auth/reset-password", json={"token": reset_token, "new_password": "OutraSenha789!"}
    )
    assert reset_response.status_code == 204

    login_response = client.post(
        "/auth/login", json={"email": VALID_REGISTER_PAYLOAD["email"], "password": "OutraSenha789!"}
    )
    assert login_response.status_code == 200


def test_unauthenticated_request_is_rejected(client):
    response = client.get("/auth/me")
    assert response.status_code == 401
