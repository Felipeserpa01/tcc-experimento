import pytest


class TestAuthAPI:
    def test_register_patient(self, client):
        """Test patient registration."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newpatient@example.com",
                "password": "SecurePass123!",
                "full_name": "New Patient"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newpatient@example.com"
        assert data["role"] == "patient"

    def test_register_duplicate_email(self, client, patient_user):
        """Test registration with duplicate email fails."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "patient@clinic.com",
                "password": "SecurePass123!",
                "full_name": "Duplicate"
            }
        )
        assert response.status_code == 409

    def test_register_weak_password(self, client):
        """Test registration with weak password fails."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "weakpass@example.com",
                "password": "weak",
                "full_name": "Weak Pass"
            }
        )
        assert response.status_code == 422

    def test_login_success(self, client, patient_user):
        """Test successful login."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "patient@clinic.com",
                "password": "PatientPass123!"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["role"] == "patient"

    def test_login_invalid_password(self, client, patient_user):
        """Test login with wrong password."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "patient@clinic.com",
                "password": "WrongPassword123!"
            }
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """Test login for non-existent user."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SomePass123!"
            }
        )
        assert response.status_code == 401

    def test_get_current_user(self, client, patient_token):
        """Test retrieving current user info."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {patient_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "patient@clinic.com"
        assert data["role"] == "patient"

    def test_get_current_user_without_token(self, client):
        """Test getting current user without token fails."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 422  # Missing header

    def test_refresh_token(self, client, patient_token, patient_user, db):
        """Test token refresh flow."""
        # First login to get refresh token
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "patient@clinic.com",
                "password": "PatientPass123!"
            }
        )
        refresh_token = login_response.json()["refresh_token"]

        # Use refresh token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_logout(self, client, patient_token):
        """Test logout revokes tokens."""
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {patient_token}"}
        )
        assert response.status_code == 200

    def test_change_password(self, client, patient_token):
        """Test password change."""
        response = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={
                "old_password": "PatientPass123!",
                "new_password": "NewPass123!"
            }
        )
        assert response.status_code == 200

    def test_change_password_wrong_old(self, client, patient_token):
        """Test password change with wrong old password."""
        response = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {patient_token}"},
            json={
                "old_password": "WrongPassword123!",
                "new_password": "NewPass123!"
            }
        )
        assert response.status_code == 401

    def test_password_reset_request(self, client):
        """Test password reset request."""
        response = client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "patient@clinic.com"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "reset_token" in data  # Demo mode returns token

    def test_password_reset_request_nonexistent(self, client):
        """Test password reset for non-existent user returns success (security)."""
        response = client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "nonexistent@example.com"}
        )
        # Should return 200 to not reveal existence of user
        assert response.status_code == 200
