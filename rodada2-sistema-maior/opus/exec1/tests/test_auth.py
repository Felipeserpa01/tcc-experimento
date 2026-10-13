"""Testes de autenticacao, bloqueio de conta, tokens e recuperacao de senha."""

from __future__ import annotations



from app.models.enums import AuditStatus, UserRole
from app.models.user import User
from tests.conftest import API, DEFAULT_PASSWORD, VALID_CPFS, auth_headers, login, make_user


class TestRegister:
    def test_registers_patient_successfully(self, client, db):
        response = client.post(
            f"{API}/auth/register",
            json={
                "email": "novo@paciente.com",
                "password": "SenhaForte@123",
                "full_name": "Novo Paciente",
                "cpf": "529.982.247-25",
                "birth_date": "1991-02-03",
                "phone": "(11) 98888-7777",
            },
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["email"] == "novo@paciente.com"
        assert body["role"] == UserRole.PATIENT.value
        assert "hashed_password" not in body

    def test_creates_linked_patient_record(self, client):
        client.post(
            f"{API}/auth/register",
            json={
                "email": "novo@paciente.com",
                "password": "SenhaForte@123",
                "full_name": "Novo Paciente",
                "cpf": VALID_CPFS[2],
                "birth_date": "1991-02-03",
                "phone": "11988887777",
            },
        )
        headers = auth_headers(client, "novo@paciente.com", "SenhaForte@123")
        response = client.get(f"{API}/patients/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["cpf"] == VALID_CPFS[2]

    def test_rejects_duplicate_email(self, client):
        payload = {
            "email": "dup@paciente.com",
            "password": "SenhaForte@123",
            "full_name": "Paciente Dup",
            "cpf": VALID_CPFS[0],
            "birth_date": "1991-02-03",
            "phone": "11988887777",
        }
        assert client.post(f"{API}/auth/register", json=payload).status_code == 201
        payload["cpf"] = VALID_CPFS[1]
        response = client.post(f"{API}/auth/register", json=payload)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "duplicate_resource"

    def test_rejects_duplicate_cpf(self, client):
        payload = {
            "email": "a@paciente.com",
            "password": "SenhaForte@123",
            "full_name": "Paciente A",
            "cpf": VALID_CPFS[0],
            "birth_date": "1991-02-03",
            "phone": "11988887777",
        }
        client.post(f"{API}/auth/register", json=payload)
        payload["email"] = "b@paciente.com"
        response = client.post(f"{API}/auth/register", json=payload)
        assert response.status_code == 409

    def test_rejects_invalid_cpf(self, client):
        response = client.post(
            f"{API}/auth/register",
            json={
                "email": "x@paciente.com",
                "password": "SenhaForte@123",
                "full_name": "Paciente X",
                "cpf": "111.111.111-11",
                "birth_date": "1991-02-03",
                "phone": "11988887777",
            },
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"

    def test_rejects_weak_password(self, client):
        response = client.post(
            f"{API}/auth/register",
            json={
                "email": "y@paciente.com",
                "password": "semsimbolo123",
                "full_name": "Paciente Y",
                "cpf": VALID_CPFS[3],
                "birth_date": "1991-02-03",
                "phone": "11988887777",
            },
        )
        assert response.status_code == 422

    def test_rejects_future_birth_date(self, client):
        response = client.post(
            f"{API}/auth/register",
            json={
                "email": "z@paciente.com",
                "password": "SenhaForte@123",
                "full_name": "Paciente Z",
                "cpf": VALID_CPFS[4],
                "birth_date": "2999-01-01",
                "phone": "11988887777",
            },
        )
        assert response.status_code == 422

    def test_rejects_single_word_name(self, client):
        response = client.post(
            f"{API}/auth/register",
            json={
                "email": "w@paciente.com",
                "password": "SenhaForte@123",
                "full_name": "Fulano",
                "cpf": VALID_CPFS[5],
                "birth_date": "1991-02-03",
                "phone": "11988887777",
            },
        )
        assert response.status_code == 422


class TestLogin:
    def test_login_returns_tokens(self, client, scenario):
        body = login(client, "admin@clinica.com")
        assert body["access_token"]
        assert body["refresh_token"]
        assert body["token_type"] == "bearer"
        assert body["expires_in"] > 0

    def test_login_is_case_insensitive_for_email(self, client, scenario):
        response = client.post(
            f"{API}/auth/login",
            json={"email": "ADMIN@Clinica.com", "password": DEFAULT_PASSWORD},
        )
        assert response.status_code == 200

    def test_wrong_password_returns_401(self, client, scenario):
        response = client.post(
            f"{API}/auth/login",
            json={"email": "admin@clinica.com", "password": "SenhaErrada@1"},
        )
        assert response.status_code == 401
        assert response.json()["error"]["message"] == "Email ou senha invalidos."

    def test_unknown_email_returns_same_message(self, client, scenario):
        response = client.post(
            f"{API}/auth/login",
            json={"email": "naoexiste@clinica.com", "password": "SenhaErrada@1"},
        )
        assert response.status_code == 401
        assert response.json()["error"]["message"] == "Email ou senha invalidos."

    def test_inactive_account_cannot_login(self, client, db, scenario):
        user = db.get(User, scenario["admin"].id)
        user.is_active = False
        db.commit()
        response = client.post(
            f"{API}/auth/login",
            json={"email": "admin@clinica.com", "password": DEFAULT_PASSWORD},
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "account_inactive"

    def test_oauth2_token_endpoint(self, client, scenario):
        response = client.post(
            f"{API}/auth/token",
            data={"username": "admin@clinica.com", "password": DEFAULT_PASSWORD},
        )
        assert response.status_code == 200
        assert response.json()["access_token"]


class TestAccountLockout:
    def _fail_login(self, client, times: int):
        last = None
        for _ in range(times):
            last = client.post(
                f"{API}/auth/login",
                json={"email": "admin@clinica.com", "password": "SenhaErrada@1"},
            )
        return last

    def test_locks_account_after_five_failures(self, client, scenario):
        for attempt in range(4):
            response = self._fail_login(client, 1)
            assert response.status_code == 401, f"tentativa {attempt + 1}"

        fifth = self._fail_login(client, 1)
        assert fifth.status_code == 423
        assert fifth.json()["error"]["code"] == "account_locked"

    def test_correct_password_blocked_while_locked(self, client, scenario):
        self._fail_login(client, 5)
        response = client.post(
            f"{API}/auth/login",
            json={"email": "admin@clinica.com", "password": DEFAULT_PASSWORD},
        )
        assert response.status_code == 423

    def test_counter_resets_after_successful_login(self, client, db, scenario):
        self._fail_login(client, 3)
        login(client, "admin@clinica.com")
        user = db.query(User).filter(User.email == "admin@clinica.com").one()
        db.refresh(user)
        assert user.failed_login_attempts == 0
        assert user.locked_until is None

    def test_admin_can_unlock_account(self, client, db, scenario):
        target = make_user(db, email="travado@clinica.com", role=UserRole.RECEPTIONIST)
        for _ in range(5):
            client.post(
                f"{API}/auth/login",
                json={"email": "travado@clinica.com", "password": "Errada@123"},
            )
        headers = auth_headers(client, "admin@clinica.com")
        response = client.post(f"{API}/users/{target.id}/unlock", headers=headers)
        assert response.status_code == 200
        assert login(client, "travado@clinica.com")["access_token"]

    def test_lockout_is_audited(self, client, scenario):
        self._fail_login(client, 5)
        headers = auth_headers(client, "recepcao@clinica.com")
        # recepcionista nao acessa auditoria
        assert client.get(f"{API}/audit-logs", headers=headers).status_code == 403


class TestTokens:
    def test_refresh_rotates_token(self, client, scenario):
        tokens = login(client, "admin@clinica.com")
        response = client.post(
            f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert response.status_code == 200
        new_tokens = response.json()
        assert new_tokens["refresh_token"] != tokens["refresh_token"]

    def test_old_refresh_token_is_revoked(self, client, scenario):
        tokens = login(client, "admin@clinica.com")
        client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        reuse = client.post(
            f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert reuse.status_code == 401
        assert reuse.json()["error"]["code"] == "invalid_token"

    def test_reuse_detection_revokes_all_sessions(self, client, db, scenario):
        tokens = login(client, "admin@clinica.com")
        rotated = client.post(
            f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        ).json()
        client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        # o token rotacionado tambem deve ter sido revogado
        response = client.post(
            f"{API}/auth/refresh", json={"refresh_token": rotated["refresh_token"]}
        )
        assert response.status_code == 401

    def test_access_token_cannot_be_used_as_refresh(self, client, scenario):
        tokens = login(client, "admin@clinica.com")
        response = client.post(
            f"{API}/auth/refresh", json={"refresh_token": tokens["access_token"]}
        )
        assert response.status_code == 401

    def test_refresh_token_cannot_authorize_requests(self, client, scenario):
        tokens = login(client, "admin@clinica.com")
        response = client.get(
            f"{API}/auth/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"}
        )
        assert response.status_code == 401

    def test_missing_token_returns_401(self, client, scenario):
        assert client.get(f"{API}/auth/me").status_code == 401

    def test_garbage_token_returns_401(self, client, scenario):
        response = client.get(
            f"{API}/auth/me", headers={"Authorization": "Bearer token-invalido"}
        )
        assert response.status_code == 401

    def test_logout_revokes_refresh_token(self, client, scenario):
        tokens = login(client, "admin@clinica.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        response = client.post(
            f"{API}/auth/logout", json={"refresh_token": tokens["refresh_token"]}, headers=headers
        )
        assert response.status_code == 200
        retry = client.post(
            f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert retry.status_code == 401

    def test_logout_all_sessions(self, client, db, scenario):
        first = login(client, "admin@clinica.com")
        second = login(client, "admin@clinica.com")
        headers = {"Authorization": f"Bearer {second['access_token']}"}
        client.post(f"{API}/auth/logout", json={"all_sessions": True}, headers=headers)
        assert (
            client.post(
                f"{API}/auth/refresh", json={"refresh_token": first["refresh_token"]}
            ).status_code
            == 401
        )


class TestMe:
    def test_returns_profile_links(self, client, scenario):
        headers = auth_headers(client, "paciente@clinica.com")
        body = client.get(f"{API}/auth/me", headers=headers).json()
        assert body["role"] == UserRole.PATIENT.value
        assert body["patient_id"] == scenario["patient"].id
        assert body["professional_id"] is None

    def test_doctor_profile_link(self, client, scenario):
        headers = auth_headers(client, "medico@clinica.com")
        body = client.get(f"{API}/auth/me", headers=headers).json()
        assert body["professional_id"] == scenario["doctor"].id


class TestChangePassword:
    def test_changes_password(self, client, scenario):
        headers = auth_headers(client, "admin@clinica.com")
        response = client.post(
            f"{API}/auth/change-password",
            json={"current_password": DEFAULT_PASSWORD, "new_password": "NovaSenha@456"},
            headers=headers,
        )
        assert response.status_code == 200
        assert login(client, "admin@clinica.com", "NovaSenha@456")["access_token"]

    def test_rejects_wrong_current_password(self, client, scenario):
        headers = auth_headers(client, "admin@clinica.com")
        response = client.post(
            f"{API}/auth/change-password",
            json={"current_password": "Errada@123", "new_password": "NovaSenha@456"},
            headers=headers,
        )
        assert response.status_code == 401

    def test_rejects_same_password(self, client, scenario):
        headers = auth_headers(client, "admin@clinica.com")
        response = client.post(
            f"{API}/auth/change-password",
            json={"current_password": DEFAULT_PASSWORD, "new_password": DEFAULT_PASSWORD},
            headers=headers,
        )
        assert response.status_code == 422

    def test_rejects_weak_new_password(self, client, scenario):
        headers = auth_headers(client, "admin@clinica.com")
        response = client.post(
            f"{API}/auth/change-password",
            json={"current_password": DEFAULT_PASSWORD, "new_password": "fraca"},
            headers=headers,
        )
        assert response.status_code == 422

    def test_sessions_revoked_after_change(self, client, scenario):
        tokens = login(client, "admin@clinica.com")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        client.post(
            f"{API}/auth/change-password",
            json={"current_password": DEFAULT_PASSWORD, "new_password": "NovaSenha@456"},
            headers=headers,
        )
        response = client.post(
            f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert response.status_code == 401


class TestPasswordRecovery:
    def test_recovery_returns_token_outside_production(self, client, scenario):
        response = client.post(
            f"{API}/auth/password-recovery", json={"email": "admin@clinica.com"}
        )
        assert response.status_code == 200
        assert response.json()["reset_token"]

    def test_recovery_response_is_neutral_for_unknown_email(self, client, scenario):
        known = client.post(
            f"{API}/auth/password-recovery", json={"email": "admin@clinica.com"}
        ).json()
        unknown = client.post(
            f"{API}/auth/password-recovery", json={"email": "ninguem@clinica.com"}
        ).json()
        assert known["message"] == unknown["message"]
        assert unknown["reset_token"] is None

    def test_reset_password_with_token(self, client, scenario):
        token = client.post(
            f"{API}/auth/password-recovery", json={"email": "admin@clinica.com"}
        ).json()["reset_token"]
        response = client.post(
            f"{API}/auth/password-reset",
            json={"token": token, "new_password": "OutraSenha@789"},
        )
        assert response.status_code == 200
        assert login(client, "admin@clinica.com", "OutraSenha@789")["access_token"]

    def test_token_is_single_use(self, client, scenario):
        token = client.post(
            f"{API}/auth/password-recovery", json={"email": "admin@clinica.com"}
        ).json()["reset_token"]
        client.post(
            f"{API}/auth/password-reset",
            json={"token": token, "new_password": "OutraSenha@789"},
        )
        response = client.post(
            f"{API}/auth/password-reset",
            json={"token": token, "new_password": "MaisUma@0123"},
        )
        assert response.status_code == 401

    def test_invalid_token_rejected(self, client, scenario):
        response = client.post(
            f"{API}/auth/password-reset",
            json={"token": "token-que-nao-existe", "new_password": "OutraSenha@789"},
        )
        assert response.status_code == 401

    def test_reset_unlocks_account(self, client, db, scenario):
        for _ in range(5):
            client.post(
                f"{API}/auth/login",
                json={"email": "admin@clinica.com", "password": "Errada@123"},
            )
        token = client.post(
            f"{API}/auth/password-recovery", json={"email": "admin@clinica.com"}
        ).json()["reset_token"]
        client.post(
            f"{API}/auth/password-reset",
            json={"token": token, "new_password": "OutraSenha@789"},
        )
        assert login(client, "admin@clinica.com", "OutraSenha@789")["access_token"]

    def test_reset_rejects_same_password(self, client, scenario):
        token = client.post(
            f"{API}/auth/password-recovery", json={"email": "admin@clinica.com"}
        ).json()["reset_token"]
        response = client.post(
            f"{API}/auth/password-reset",
            json={"token": token, "new_password": DEFAULT_PASSWORD},
        )
        assert response.status_code == 422


class TestAuditTrail:
    def test_login_is_recorded(self, client, scenario):
        login(client, "admin@clinica.com")
        headers = auth_headers(client, "admin@clinica.com")
        response = client.get(
            f"{API}/audit-logs", params={"action": "auth.login"}, headers=headers
        )
        assert response.status_code == 200
        actions = {item["action"] for item in response.json()["items"]}
        assert "auth.login.success" in actions

    def test_failed_login_is_recorded_with_failure_status(self, client, scenario):
        client.post(
            f"{API}/auth/login",
            json={"email": "admin@clinica.com", "password": "Errada@123"},
        )
        headers = auth_headers(client, "admin@clinica.com")
        response = client.get(
            f"{API}/audit-logs",
            params={"action": "auth.login.failed", "status": AuditStatus.FAILURE.value},
            headers=headers,
        )
        assert response.json()["meta"]["total"] >= 1

    def test_audit_is_admin_only(self, client, scenario):
        headers = auth_headers(client, "medico@clinica.com")
        assert client.get(f"{API}/audit-logs", headers=headers).status_code == 403
