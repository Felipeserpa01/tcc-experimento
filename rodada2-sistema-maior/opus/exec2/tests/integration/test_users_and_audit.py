from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import Role
from app.models.patient import Patient
from app.models.professional import Professional
from app.models.user import User
from tests.factories import API, PASSWORD, make_doctor, make_nurse, make_patient, token_for

NEW_USER = {
    "email": "nova@clinica.com.br",
    "full_name": "Nova Recepcionista",
    "password": "Recep@2030",
    "role": "recepcionista",
}


class TestUserAdministration:
    def test_admin_creates_receptionist(self, client: TestClient, admin_h: dict) -> None:
        response = client.post(f"{API}/users", json=NEW_USER, headers=admin_h)
        assert response.status_code == 201
        assert response.json()["role"] == "recepcionista"
        login = client.post(f"{API}/auth/login", json={"email": NEW_USER["email"], "password": NEW_USER["password"]})
        assert login.status_code == 200

    def test_only_admin_manages_users(
        self, client: TestClient, reception_h: dict, doctor_h: dict, patient_h: dict
    ) -> None:
        for headers in (reception_h, doctor_h, patient_h):
            response = client.post(f"{API}/users", json=NEW_USER, headers=headers)
            assert response.status_code == 403
            assert response.json()["error"]["code"] == "acesso_negado"

    def test_create_doctor_user_linked_to_professional(self, client: TestClient, admin_h: dict, db: Session) -> None:
        professional = make_doctor(db, with_user=False)
        payload = {**NEW_USER, "email": "dr@clinica.com.br", "role": "medico", "professional_id": professional.id}
        response = client.post(f"{API}/users", json=payload, headers=admin_h)
        assert response.status_code == 201
        assert response.json()["professional_id"] == professional.id
        # O mesmo profissional não pode ter dois usuários.
        again = client.post(f"{API}/users", json={**payload, "email": "dr2@clinica.com.br"}, headers=admin_h)
        assert again.status_code == 409

    def test_role_must_match_professional_type(self, client: TestClient, admin_h: dict, db: Session) -> None:
        nurse = make_nurse(db, with_user=False)
        payload = {**NEW_USER, "role": "medico", "professional_id": nurse.id}
        assert client.post(f"{API}/users", json=payload, headers=admin_h).status_code == 422

    def test_link_rules_are_validated(self, client: TestClient, admin_h: dict, db: Session) -> None:
        patient = make_patient(db)
        missing_link = client.post(f"{API}/users", json={**NEW_USER, "role": "paciente"}, headers=admin_h)
        assert missing_link.status_code == 422
        receptionist_with_link = client.post(
            f"{API}/users", json={**NEW_USER, "patient_id": patient.id}, headers=admin_h
        )
        assert receptionist_with_link.status_code == 422
        ok = client.post(
            f"{API}/users", json={**NEW_USER, "role": "paciente", "patient_id": patient.id}, headers=admin_h
        )
        assert ok.status_code == 201

    def test_duplicate_email(self, client: TestClient, admin_h: dict, admin: User) -> None:
        response = client.post(f"{API}/users", json={**NEW_USER, "email": "ADMIN@clinica.com.br"}, headers=admin_h)
        assert response.status_code == 409

    def test_deactivating_user_revokes_access(self, client: TestClient, admin_h: dict, receptionist: User) -> None:
        headers = token_for(receptionist)
        assert client.get(f"{API}/auth/me", headers=headers).status_code == 200
        response = client.patch(f"{API}/users/{receptionist.id}", json={"is_active": False}, headers=admin_h)
        assert response.status_code == 200
        assert client.get(f"{API}/auth/me", headers=headers).status_code == 401
        login = client.post(f"{API}/auth/login", json={"email": receptionist.email, "password": PASSWORD})
        assert login.status_code == 403

    def test_admin_cannot_deactivate_self(self, client: TestClient, admin_h: dict, admin: User) -> None:
        response = client.patch(f"{API}/users/{admin.id}", json={"is_active": False}, headers=admin_h)
        assert response.status_code == 422

    def test_list_users_with_filters_and_pagination(
        self, client: TestClient, admin_h: dict, receptionist: User, doctor: Professional, patient: Patient
    ) -> None:
        response = client.get(f"{API}/users", params={"role": "medico"}, headers=admin_h)
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["role"] == "medico"

        paged = client.get(
            f"{API}/users", params={"page_size": 2, "sort_by": "email", "sort_order": "desc"}, headers=admin_h
        )
        assert paged.json()["page_size"] == 2
        assert paged.json()["pages"] == 2
        emails = [u["email"] for u in paged.json()["items"]]
        assert emails == sorted(emails, reverse=True)

    def test_invalid_sort_field(self, client: TestClient, admin_h: dict) -> None:
        response = client.get(f"{API}/users", params={"sort_by": "hashed_password"}, headers=admin_h)
        assert response.status_code == 422
        assert "Opções permitidas" in response.json()["error"]["details"][0]["message"]


class TestAuditLog:
    def test_sensitive_actions_are_audited(self, client: TestClient, admin_h: dict, admin: User) -> None:
        client.post(f"{API}/users", json=NEW_USER, headers=admin_h)
        client.post(f"{API}/auth/login", json={"email": "admin@clinica.com.br", "password": "Errada@123"})

        response = client.get(f"{API}/audit-logs", params={"action": "usuario.criado"}, headers=admin_h)
        assert response.status_code == 200
        entry = response.json()["items"][0]
        assert entry["user_id"] == admin.id
        assert entry["user_email"] == "admin@clinica.com.br"
        assert entry["entity_type"] == "usuario"
        assert entry["ip_address"] == "testclient"
        assert entry["created_at"].startswith("2030-01-07")

        failures = client.get(f"{API}/audit-logs", params={"action": "auth.login.falha"}, headers=admin_h).json()
        assert failures["total"] == 1
        assert "senha" not in str(failures["items"][0]["details"]).lower() or "senha_incorreta" in str(
            failures["items"][0]["details"]
        )

    def test_audit_log_is_admin_only(self, client: TestClient, reception_h: dict, doctor_h: dict) -> None:
        assert client.get(f"{API}/audit-logs", headers=reception_h).status_code == 403
        assert client.get(f"{API}/audit-logs", headers=doctor_h).status_code == 403

    def test_invalid_date_range(self, client: TestClient, admin_h: dict) -> None:
        response = client.get(
            f"{API}/audit-logs", params={"date_from": "2030-02-01", "date_to": "2030-01-01"}, headers=admin_h
        )
        assert response.status_code == 422


class TestGeneralBehaviour:
    def test_health(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert "X-Request-ID" in response.headers

    def test_unknown_route_uses_standard_error_format(self, client: TestClient) -> None:
        response = client.get(f"{API}/nao-existe")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "nao_encontrado"

    def test_malformed_json(self, client: TestClient) -> None:
        response = client.post(
            f"{API}/auth/login", content=b"{nao e json", headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
        assert response.json()["error"]["details"][0]["message"] == "JSON malformado."

    def test_initial_admin_bootstrap(self, engine, monkeypatch) -> None:
        from app.core.config import get_settings
        from app.main import create_app

        monkeypatch.setenv("INITIAL_ADMIN_EMAIL", "root@clinica.com.br")
        monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", "Root#2030pass")
        get_settings.cache_clear()
        try:
            with TestClient(create_app()) as client:
                login = client.post(
                    f"{API}/auth/login", json={"email": "root@clinica.com.br", "password": "Root#2030pass"}
                )
                assert login.status_code == 200
        finally:
            monkeypatch.delenv("INITIAL_ADMIN_EMAIL")
            monkeypatch.delenv("INITIAL_ADMIN_PASSWORD")
            get_settings.cache_clear()

    def test_roles_listing_contains_five_profiles(self) -> None:
        assert {role.value for role in Role} == {"administrador", "medico", "enfermeiro", "recepcionista", "paciente"}
