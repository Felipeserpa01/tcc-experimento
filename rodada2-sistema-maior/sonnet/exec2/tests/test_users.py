"""Integration tests for admin-only staff user management."""
from tests.conftest import VALID_PASSWORD


def test_admin_can_create_staff_user(client, admin_headers):
    resp = client.post(
        "/users",
        json={"email": "nova.recepcao@clinica.com", "password": VALID_PASSWORD, "role": "recepcionista"},
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["role"] == "recepcionista"


def test_staff_creation_rejects_clinical_roles(client, admin_headers):
    resp = client.post(
        "/users",
        json={"email": "medico.via.users@clinica.com", "password": VALID_PASSWORD, "role": "medico"},
        headers=admin_headers,
    )
    assert resp.status_code == 422


def test_non_admin_cannot_create_staff_user(client, recepcionista_headers):
    resp = client.post(
        "/users",
        json={"email": "outra.recepcao@clinica.com", "password": VALID_PASSWORD, "role": "recepcionista"},
        headers=recepcionista_headers,
    )
    assert resp.status_code == 403


def test_admin_can_list_users(client, admin_headers, recepcionista_headers):
    resp = client.get("/users", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    # admin_headers and recepcionista_headers fixtures each create one user.
    assert body["total"] == 2


def test_admin_can_deactivate_and_reactivate_user(client, admin_headers, db_session):
    from app.core.enums import UserRole
    from tests.conftest import create_user

    target = create_user(db_session, "alvo@clinica.com", UserRole.RECEPCIONISTA)

    deactivated = client.patch(f"/users/{target.id}/deactivate", headers=admin_headers)
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    blocked_login = client.post(
        "/auth/login", json={"email": "alvo@clinica.com", "password": VALID_PASSWORD}
    )
    assert blocked_login.status_code == 403

    reactivated = client.patch(f"/users/{target.id}/activate", headers=admin_headers)
    assert reactivated.status_code == 200
    assert reactivated.json()["is_active"] is True

    allowed_login = client.post(
        "/auth/login", json={"email": "alvo@clinica.com", "password": VALID_PASSWORD}
    )
    assert allowed_login.status_code == 200


def test_deactivate_nonexistent_user_returns_404(client, admin_headers):
    resp = client.patch("/users/9999/deactivate", headers=admin_headers)
    assert resp.status_code == 404
