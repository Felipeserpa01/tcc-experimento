"""Testes de gestao de usuarios, tratamento de erros e infraestrutura."""

from __future__ import annotations

import pytest

from app.models.enums import UserRole
from tests.conftest import API, DEFAULT_PASSWORD, auth_headers, login, make_user


@pytest.fixture()
def admin_headers(client, scenario):
    return auth_headers(client, "admin@clinica.com")


class TestUserManagement:
    def test_admin_creates_staff_user(self, client, admin_headers):
        response = client.post(
            f"{API}/users",
            json={
                "email": "novo.medico@clinica.com",
                "password": "SenhaForte@123",
                "full_name": "Novo Medico",
                "role": "doctor",
            },
            headers=admin_headers,
        )
        assert response.status_code == 201
        assert response.json()["role"] == "doctor"

    def test_rejects_duplicate_email(self, client, admin_headers):
        response = client.post(
            f"{API}/users",
            json={
                "email": "admin@clinica.com",
                "password": "SenhaForte@123",
                "full_name": "Outro Admin",
                "role": "admin",
            },
            headers=admin_headers,
        )
        assert response.status_code == 409

    def test_rejects_invalid_role(self, client, admin_headers):
        response = client.post(
            f"{API}/users",
            json={
                "email": "x@clinica.com",
                "password": "SenhaForte@123",
                "full_name": "Perfil Invalido",
                "role": "superuser",
            },
            headers=admin_headers,
        )
        assert response.status_code == 422

    def test_non_admin_cannot_list_users(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.get(f"{API}/users", headers=headers)
        assert response.status_code == 403
        assert response.json()["error"]["details"]["your_role"] == "receptionist"

    def test_filter_users_by_role(self, client, admin_headers):
        response = client.get(f"{API}/users", params={"role": "doctor"}, headers=admin_headers)
        assert response.json()["meta"]["total"] == 2

    def test_search_users_by_name(self, client, admin_headers):
        response = client.get(f"{API}/users", params={"query": "Rita"}, headers=admin_headers)
        assert response.json()["meta"]["total"] == 1

    def test_deactivate_and_activate(self, client, db, admin_headers):
        target = make_user(db, email="temp@clinica.com", role=UserRole.RECEPTIONIST)
        deactivated = client.post(f"{API}/users/{target.id}/deactivate", headers=admin_headers)
        assert deactivated.json()["is_active"] is False
        assert (
            client.post(
                f"{API}/auth/login",
                json={"email": "temp@clinica.com", "password": DEFAULT_PASSWORD},
            ).status_code
            == 403
        )
        activated = client.post(f"{API}/users/{target.id}/activate", headers=admin_headers)
        assert activated.json()["is_active"] is True

    def test_admin_cannot_deactivate_self(self, client, scenario, admin_headers):
        response = client.post(
            f"{API}/users/{scenario['admin'].id}/deactivate", headers=admin_headers
        )
        assert response.status_code == 422

    def test_cannot_remove_last_active_admin(self, client, db, scenario, admin_headers):
        second_admin = make_user(db, email="admin2@clinica.com", role=UserRole.ADMIN)
        headers = auth_headers(client, "admin2@clinica.com")
        client.post(f"{API}/users/{scenario['admin'].id}/deactivate", headers=headers)
        response = client.patch(
            f"{API}/users/{second_admin.id}", json={"role": "receptionist"}, headers=headers
        )
        assert response.status_code == 422

    def test_admin_resets_user_password(self, client, db, admin_headers):
        target = make_user(db, email="reset@clinica.com", role=UserRole.NURSE)
        response = client.post(
            f"{API}/users/{target.id}/reset-password",
            json={"new_password": "NovaSenha@456"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert login(client, "reset@clinica.com", "NovaSenha@456")["access_token"]

    def test_reset_password_enforces_policy(self, client, db, admin_headers):
        target = make_user(db, email="reset2@clinica.com", role=UserRole.NURSE)
        response = client.post(
            f"{API}/users/{target.id}/reset-password",
            json={"new_password": "fraca123"},
            headers=admin_headers,
        )
        assert response.status_code == 422

    def test_unknown_user_returns_404(self, client, admin_headers):
        response = client.get(f"{API}/users/9999", headers=admin_headers)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"


class TestErrorEnvelope:
    def test_error_has_code_message_and_request_id(self, client, scenario):
        response = client.get(f"{API}/patients/9999", headers=auth_headers(client, "admin@clinica.com"))
        error = response.json()["error"]
        assert set(["code", "message", "request_id"]).issubset(error.keys())

    def test_request_id_header_is_present(self, client):
        response = client.get("/health")
        assert response.headers.get("X-Request-ID")

    def test_validation_error_lists_fields(self, client, scenario):
        headers = auth_headers(client, "recepcao@clinica.com")
        response = client.post(f"{API}/patients", json={"full_name": "So Nome"}, headers=headers)
        assert response.status_code == 422
        fields = {item["field"] for item in response.json()["error"]["details"]}
        assert "cpf" in fields
        assert "birth_date" in fields

    def test_unauthenticated_sets_www_authenticate(self, client):
        response = client.get(f"{API}/patients")
        assert response.status_code == 401
        assert response.headers.get("WWW-Authenticate") == "Bearer"

    def test_unknown_route_returns_structured_404(self, client):
        response = client.get(f"{API}/rota-inexistente")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"

    def test_method_not_allowed(self, client):
        response = client.delete(f"{API}/auth/login")
        assert response.status_code == 405
        assert response.json()["error"]["code"] == "method_not_allowed"

    def test_invalid_path_parameter_type(self, client, scenario):
        headers = auth_headers(client, "admin@clinica.com")
        response = client.get(f"{API}/patients/abc", headers=headers)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"


class TestNotifications:
    def test_list_is_scoped_to_user(self, client, scenario):
        headers = auth_headers(client, "paciente@clinica.com")
        response = client.get(f"{API}/notifications", headers=headers)
        assert response.status_code == 200
        assert response.json()["meta"]["total"] == 0

    def test_mark_as_read(self, client, scenario):
        reception = auth_headers(client, "recepcao@clinica.com")
        patient = auth_headers(client, "paciente@clinica.com")
        from tests.conftest import next_weekday_at

        appointment = client.post(
            f"{API}/appointments",
            json={
                "patient_id": scenario["patient"].id,
                "professional_id": scenario["doctor"].id,
                "scheduled_start": next_weekday_at(9).isoformat(),
            },
            headers=reception,
        ).json()
        client.post(f"{API}/appointments/{appointment['id']}/confirm", headers=reception)

        listing = client.get(f"{API}/notifications", headers=patient).json()
        assert listing["meta"]["total"] == 1
        notification_id = listing["items"][0]["id"]

        response = client.post(f"{API}/notifications/{notification_id}/read", headers=patient)
        assert response.status_code == 200
        assert response.json()["read_at"] is not None

    def test_cannot_read_other_users_notification(self, client, scenario):
        reception = auth_headers(client, "recepcao@clinica.com")
        patient = auth_headers(client, "paciente@clinica.com")
        other = auth_headers(client, "paciente2@clinica.com")
        from tests.conftest import next_weekday_at

        appointment = client.post(
            f"{API}/appointments",
            json={
                "patient_id": scenario["patient"].id,
                "professional_id": scenario["doctor"].id,
                "scheduled_start": next_weekday_at(9).isoformat(),
            },
            headers=reception,
        ).json()
        client.post(f"{API}/appointments/{appointment['id']}/confirm", headers=reception)
        notification_id = client.get(f"{API}/notifications", headers=patient).json()["items"][0]["id"]

        response = client.post(f"{API}/notifications/{notification_id}/read", headers=other)
        assert response.status_code == 403

    def test_mark_all_read(self, client, scenario):
        headers = auth_headers(client, "paciente@clinica.com")
        response = client.post(f"{API}/notifications/read-all", headers=headers)
        assert response.status_code == 200


class TestInfrastructure:
    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_root(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["api_prefix"] == API

    def test_openapi_is_generated(self, client):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        assert f"{API}/appointments" in response.json()["paths"]
