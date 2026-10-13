from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.enums import Role
from app.models.user import User
from tests.conftest import FakeEmailSender, FrozenClock
from tests.factories import API, PASSWORD, make_user

REGISTER_PAYLOAD = {
    "email": "Novo.Paciente@Email.com",
    "password": "Forte#2030",
    "full_name": "Pedro Álvares",
    "cpf": "529.982.247-25",
    "birth_date": "1985-03-10",
    "sex": "masculino",
    "phone": "(11) 91234-5678",
    "address": {
        "street": "Av. Paulista",
        "number": "1000",
        "neighborhood": "Bela Vista",
        "city": "São Paulo",
        "state": "sp",
        "zip_code": "01310-100",
    },
}


def login(client: TestClient, email: str, password: str = PASSWORD):
    return client.post(f"{API}/auth/login", json={"email": email, "password": password})


class TestRegister:
    def test_register_creates_patient_user(self, client: TestClient) -> None:
        response = client.post(f"{API}/auth/register", json=REGISTER_PAYLOAD)
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["role"] == "paciente"
        assert body["email"] == "novo.paciente@email.com"
        assert body["patient_id"] is not None

        tokens = login(client, "novo.paciente@email.com", "Forte#2030").json()
        me = client.get(f"{API}/patients/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
        assert me.status_code == 200
        assert me.json()["cpf"] == "52998224725"
        assert me.json()["address"]["state"] == "SP"

    def test_weak_password_is_rejected_with_clear_message(self, client: TestClient) -> None:
        response = client.post(f"{API}/auth/register", json={**REGISTER_PAYLOAD, "password": "senhafraca"})
        assert response.status_code == 422
        error = response.json()["error"]
        assert error["code"] == "dados_invalidos"
        detail = next(d for d in error["details"] if d["field"] == "password")
        assert "número" in detail["message"] and "símbolo" in detail["message"]

    def test_invalid_cpf_is_rejected(self, client: TestClient) -> None:
        response = client.post(f"{API}/auth/register", json={**REGISTER_PAYLOAD, "cpf": "529.982.247-26"})
        assert response.status_code == 422
        assert response.json()["error"]["details"][0]["field"] == "cpf"

    def test_duplicate_email_and_cpf(self, client: TestClient) -> None:
        assert client.post(f"{API}/auth/register", json=REGISTER_PAYLOAD).status_code == 201
        same_email = client.post(f"{API}/auth/register", json={**REGISTER_PAYLOAD, "cpf": "111.444.777-35"})
        assert same_email.status_code == 409
        same_cpf = client.post(f"{API}/auth/register", json={**REGISTER_PAYLOAD, "email": "outro@email.com"})
        assert same_cpf.status_code == 409
        assert "CPF" in same_cpf.json()["error"]["message"]

    def test_register_cannot_choose_role(self, client: TestClient) -> None:
        response = client.post(f"{API}/auth/register", json={**REGISTER_PAYLOAD, "role": "administrador"})
        assert response.status_code == 422
        assert response.json()["error"]["details"][0]["type"] == "extra_forbidden"


class TestLogin:
    def test_login_returns_access_and_refresh_tokens(self, client: TestClient, admin: User) -> None:
        response = login(client, "ADMIN@clinica.com.br")
        assert response.status_code == 200
        body = response.json()
        assert body["token_type"] == "bearer"
        assert body["expires_in"] == 15 * 60
        assert body["refresh_expires_in"] == 7 * 24 * 3600
        me = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
        assert me.json()["role"] == "administrador"

    def test_wrong_password_and_unknown_user_return_same_error(self, client: TestClient, admin: User) -> None:
        wrong = login(client, "admin@clinica.com.br", "Errada@123")
        unknown = login(client, "ninguem@clinica.com.br", "Errada@123")
        assert wrong.status_code == unknown.status_code == 401
        assert wrong.json()["error"]["message"] == unknown.json()["error"]["message"]

    def test_account_locks_after_five_failures(
        self, client: TestClient, admin: User, db: Session, frozen_clock: FrozenClock
    ) -> None:
        for _ in range(4):
            assert login(client, "admin@clinica.com.br", "Errada@123").status_code == 401
        fifth = login(client, "admin@clinica.com.br", "Errada@123")
        assert fifth.status_code == 423
        assert fifth.json()["error"]["code"] == "conta_bloqueada"

        # Mesmo com a senha correta, a conta segue bloqueada durante o período.
        assert login(client, "admin@clinica.com.br").status_code == 423
        frozen_clock.advance(minutes=14)
        assert login(client, "admin@clinica.com.br").status_code == 423

        frozen_clock.advance(minutes=2)
        assert login(client, "admin@clinica.com.br").status_code == 200

        actions = db.scalars(select(AuditLog.action).where(AuditLog.user_id == admin.id)).all()
        assert "auth.conta.bloqueada" in actions
        assert "auth.login.bloqueado" in actions

    def test_successful_login_resets_failure_counter(self, client: TestClient, admin: User) -> None:
        for _ in range(4):
            login(client, "admin@clinica.com.br", "Errada@123")
        assert login(client, "admin@clinica.com.br").status_code == 200
        for _ in range(4):
            assert login(client, "admin@clinica.com.br", "Errada@123").status_code == 401

    def test_inactive_user_cannot_login(self, client: TestClient, db: Session) -> None:
        user = make_user(db, Role.RECEPTIONIST, email="inativa@clinica.com.br")
        user.is_active = False
        db.commit()
        response = login(client, "inativa@clinica.com.br")
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "conta_inativa"

    def test_admin_can_unlock_account(self, client: TestClient, admin_h: dict, receptionist: User) -> None:
        for _ in range(5):
            login(client, "recepcao@clinica.com.br", "Errada@123")
        assert login(client, "recepcao@clinica.com.br").status_code == 423
        unlock = client.post(f"{API}/users/{receptionist.id}/unlock", headers=admin_h)
        assert unlock.status_code == 200
        assert login(client, "recepcao@clinica.com.br").status_code == 200


class TestTokens:
    def test_missing_or_invalid_token(self, client: TestClient) -> None:
        missing = client.get(f"{API}/auth/me")
        assert missing.status_code == 401
        assert missing.headers["WWW-Authenticate"] == "Bearer"
        invalid = client.get(f"{API}/auth/me", headers={"Authorization": "Bearer abc.def.ghi"})
        assert invalid.status_code == 401

    def test_refresh_rotates_and_detects_reuse(self, client: TestClient, admin: User) -> None:
        first = login(client, "admin@clinica.com.br").json()
        rotated = client.post(f"{API}/auth/refresh", json={"refresh_token": first["refresh_token"]})
        assert rotated.status_code == 200
        second = rotated.json()
        assert second["refresh_token"] != first["refresh_token"]

        reuse = client.post(f"{API}/auth/refresh", json={"refresh_token": first["refresh_token"]})
        assert reuse.status_code == 401
        assert reuse.json()["error"]["code"] == "token_reutilizado"
        # A reutilização revoga também o token legítimo mais recente.
        assert client.post(f"{API}/auth/refresh", json={"refresh_token": second["refresh_token"]}).status_code == 401

    def test_access_token_cannot_be_used_to_refresh(self, client: TestClient, admin: User) -> None:
        tokens = login(client, "admin@clinica.com.br").json()
        response = client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["access_token"]})
        assert response.status_code == 401

    def test_refresh_token_cannot_be_used_as_access_token(self, client: TestClient, admin: User) -> None:
        tokens = login(client, "admin@clinica.com.br").json()
        response = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"})
        assert response.status_code == 401

    def test_logout_revokes_refresh_token(self, client: TestClient, admin: User) -> None:
        tokens = login(client, "admin@clinica.com.br").json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        assert (
            client.post(
                f"{API}/auth/logout", json={"refresh_token": tokens["refresh_token"]}, headers=headers
            ).status_code
            == 204
        )
        response = client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "token_revogado"


class TestPasswordManagement:
    def test_change_password_invalidates_existing_tokens(self, client: TestClient, admin: User) -> None:
        tokens = login(client, "admin@clinica.com.br").json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        response = client.post(
            f"{API}/auth/change-password",
            json={"current_password": PASSWORD, "new_password": "NovaSenha#2030"},
            headers=headers,
        )
        assert response.status_code == 200
        assert client.get(f"{API}/auth/me", headers=headers).status_code == 401
        assert client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
        assert login(client, "admin@clinica.com.br").status_code == 401
        assert login(client, "admin@clinica.com.br", "NovaSenha#2030").status_code == 200

    def test_change_password_validations(self, client: TestClient, admin_h: dict) -> None:
        wrong = client.post(
            f"{API}/auth/change-password",
            json={"current_password": "Errada@1", "new_password": "NovaSenha#2030"},
            headers=admin_h,
        )
        assert wrong.status_code == 401
        same = client.post(
            f"{API}/auth/change-password",
            json={"current_password": PASSWORD, "new_password": PASSWORD},
            headers=admin_h,
        )
        assert same.status_code == 422
        weak = client.post(
            f"{API}/auth/change-password",
            json={"current_password": PASSWORD, "new_password": "fraca"},
            headers=admin_h,
        )
        assert weak.status_code == 422

    def test_password_recovery_flow(
        self, client: TestClient, admin: User, mailer: FakeEmailSender, frozen_clock: FrozenClock
    ) -> None:
        response = client.post(f"{API}/auth/forgot-password", json={"email": "admin@clinica.com.br"})
        assert response.status_code == 202
        assert len(mailer.outbox) == 1
        token = mailer.outbox[0].body.split("\n\n")[2].strip()

        reset = client.post(f"{API}/auth/reset-password", json={"token": token, "new_password": "Recuperada#1"})
        assert reset.status_code == 200
        assert login(client, "admin@clinica.com.br", "Recuperada#1").status_code == 200

        reused = client.post(f"{API}/auth/reset-password", json={"token": token, "new_password": "Outra#Senha2"})
        assert reused.status_code == 401

    def test_recovery_does_not_reveal_unknown_email(self, client: TestClient, mailer: FakeEmailSender) -> None:
        response = client.post(f"{API}/auth/forgot-password", json={"email": "naoexiste@clinica.com.br"})
        assert response.status_code == 202
        assert mailer.outbox == []

    def test_expired_recovery_token(
        self, client: TestClient, admin: User, mailer: FakeEmailSender, frozen_clock: FrozenClock
    ) -> None:
        client.post(f"{API}/auth/forgot-password", json={"email": "admin@clinica.com.br"})
        token = mailer.outbox[0].body.split("\n\n")[2].strip()
        frozen_clock.advance(minutes=31)
        response = client.post(f"{API}/auth/reset-password", json={"token": token, "new_password": "Recuperada#1"})
        assert response.status_code == 401

    def test_new_recovery_request_invalidates_previous_token(
        self, client: TestClient, admin: User, mailer: FakeEmailSender
    ) -> None:
        client.post(f"{API}/auth/forgot-password", json={"email": "admin@clinica.com.br"})
        client.post(f"{API}/auth/forgot-password", json={"email": "admin@clinica.com.br"})
        first = mailer.outbox[0].body.split("\n\n")[2].strip()
        second = mailer.outbox[1].body.split("\n\n")[2].strip()
        assert (
            client.post(f"{API}/auth/reset-password", json={"token": first, "new_password": "Recuperada#1"}).status_code
            == 401
        )
        assert (
            client.post(
                f"{API}/auth/reset-password", json={"token": second, "new_password": "Recuperada#1"}
            ).status_code
            == 200
        )
