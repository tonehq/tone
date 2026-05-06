"""Tests for Auth API endpoints (Core edition).

Source: core/api/v1/auth.py
All endpoints are public (no auth required).
"""

import pytest
from unittest.mock import patch, MagicMock, ANY
from fastapi import HTTPException
from fastapi.testclient import TestClient

from main import app, api_v1
from core.database.session import get_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def public_client(mock_db):
    """Client with only DB override -- no auth needed for auth endpoints."""
    api_v1.dependency_overrides[get_db] = lambda: mock_db
    client = TestClient(app)
    yield client
    api_v1.dependency_overrides.clear()


@pytest.fixture
def sample_user():
    return {
        "id": 1,
        "email": "user@example.com",
        "username": "testuser",
        "is_verified": True,
    }


@pytest.fixture
def signup_payload():
    return {
        "email": "newuser@example.com",
        "password": "SecurePass123!",
        "username": "newuser",
    }


@pytest.fixture
def login_payload():
    return {"email": "user@example.com", "password": "SecurePass123!"}


# ---------------------------------------------------------------------------
# POST /api/v1/auth/signup
# ---------------------------------------------------------------------------

class TestSignup:
    """Tests for POST /api/v1/auth/signup"""

    @patch("ee.api.v1.auth.AuthService")
    def test_success(self, mock_service_cls, public_client, signup_payload, sample_user):
        mock_service_cls.return_value.signup.return_value = sample_user
        resp = public_client.post("/api/v1/auth/signup", json=signup_payload)
        assert resp.status_code == 201
        mock_service_cls.return_value.signup.assert_called_once_with(
            "newuser@example.com", "SecurePass123!", "newuser", {},
        )

    @patch("ee.api.v1.auth.AuthService")
    def test_success_without_username(self, mock_service_cls, public_client, sample_user):
        mock_service_cls.return_value.signup.return_value = sample_user
        resp = public_client.post(
            "/api/v1/auth/signup",
            json={"email": "a@b.com", "password": "pass123"},
        )
        assert resp.status_code == 201
        mock_service_cls.return_value.signup.assert_called_once_with(
            "a@b.com", "pass123", None, {},
        )

    def test_missing_email(self, public_client):
        resp = public_client.post("/api/v1/auth/signup", json={"password": "pass123"})
        assert resp.status_code == 400

    def test_missing_password(self, public_client):
        resp = public_client.post("/api/v1/auth/signup", json={"email": "a@b.com"})
        assert resp.status_code == 400

    def test_missing_both(self, public_client):
        resp = public_client.post("/api/v1/auth/signup", json={})
        assert resp.status_code == 400

    @patch("ee.api.v1.auth.AuthService")
    def test_duplicate_email(self, mock_service_cls, public_client, signup_payload):
        mock_service_cls.return_value.signup.side_effect = HTTPException(
            status_code=409, detail="Email already registered"
        )
        resp = public_client.post("/api/v1/auth/signup", json=signup_payload)
        assert resp.status_code == 409

    @patch("ee.api.v1.auth.AuthService")
    def test_service_error(self, mock_service_cls, public_client, signup_payload):
        mock_service_cls.return_value.signup.side_effect = HTTPException(status_code=500, detail="DB error")
        resp = public_client.post("/api/v1/auth/signup", json=signup_payload)
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# POST /api/v1/auth/signup_with_firebase
# ---------------------------------------------------------------------------

class TestSignupWithFirebase:
    """Tests for POST /api/v1/auth/signup_with_firebase"""

    @patch("ee.api.v1.auth.AuthService")
    def test_success(self, mock_service_cls, public_client, sample_user):
        mock_service_cls.return_value.signup_with_firebase.return_value = sample_user
        resp = public_client.post(
            "/api/v1/auth/signup_with_firebase",
            json={"email": "user@example.com"},
            headers={"Authorization": "Bearer firebase-token-123"},
        )
        assert resp.status_code == 201
        mock_service_cls.return_value.signup_with_firebase.assert_called_once_with(
            "firebase-token-123", "user@example.com", None,
        )

    def test_missing_email(self, public_client):
        resp = public_client.post(
            "/api/v1/auth/signup_with_firebase",
            json={},
            headers={"Authorization": "Bearer token"},
        )
        assert resp.status_code == 400

    def test_missing_authorization_header(self, public_client):
        resp = public_client.post(
            "/api/v1/auth/signup_with_firebase",
            json={"email": "user@example.com"},
        )
        assert resp.status_code == 422

    def test_invalid_authorization_header(self, public_client):
        resp = public_client.post(
            "/api/v1/auth/signup_with_firebase",
            json={"email": "user@example.com"},
            headers={"Authorization": "Basic abc123"},
        )
        assert resp.status_code == 401

    @patch("ee.api.v1.auth.AuthService")
    def test_service_error(self, mock_service_cls, public_client):
        mock_service_cls.return_value.signup_with_firebase.side_effect = Exception("Firebase error")
        resp = public_client.post(
            "/api/v1/auth/signup_with_firebase",
            json={"email": "user@example.com"},
            headers={"Authorization": "Bearer token"},
        )
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/auth/resend_verification_email
# ---------------------------------------------------------------------------

class TestResendVerificationEmail:
    """Tests for GET /api/v1/auth/resend_verification_email"""

    @patch("ee.api.v1.auth.AuthService")
    def test_success(self, mock_service_cls, public_client):
        mock_service_cls.return_value.resend_verification_email.return_value = {
            "message": "Verification email sent"
        }
        resp = public_client.get(
            "/api/v1/auth/resend_verification_email", params={"email": "user@example.com"}
        )
        assert resp.status_code == 200

    def test_missing_email(self, public_client):
        resp = public_client.get("/api/v1/auth/resend_verification_email")
        assert resp.status_code == 422

    @patch("ee.api.v1.auth.AuthService")
    def test_service_error(self, mock_service_cls, public_client):
        mock_service_cls.return_value.resend_verification_email.side_effect = Exception("err")
        resp = public_client.get(
            "/api/v1/auth/resend_verification_email", params={"email": "user@example.com"}
        )
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/auth/verify_user_email
# ---------------------------------------------------------------------------

class TestVerifyUserEmail:
    """Tests for GET /api/v1/auth/verify_user_email"""

    @patch("ee.api.v1.auth.AuthService")
    def test_success(self, mock_service_cls, public_client):
        mock_service_cls.return_value.verify_user_email.return_value = {"message": "Verified"}
        resp = public_client.get(
            "/api/v1/auth/verify_user_email",
            params={"email": "user@example.com", "code": "123456", "user_id": 1},
        )
        assert resp.status_code == 200
        mock_service_cls.return_value.verify_user_email.assert_called_once_with(
            "user@example.com", "123456", 1,
        )

    def test_missing_email(self, public_client):
        resp = public_client.get(
            "/api/v1/auth/verify_user_email",
            params={"code": "123456", "user_id": 1},
        )
        assert resp.status_code == 422

    def test_missing_code(self, public_client):
        resp = public_client.get(
            "/api/v1/auth/verify_user_email",
            params={"email": "user@example.com", "user_id": 1},
        )
        assert resp.status_code == 422

    def test_missing_user_id(self, public_client):
        resp = public_client.get(
            "/api/v1/auth/verify_user_email",
            params={"email": "user@example.com", "code": "123456"},
        )
        assert resp.status_code == 422

    @patch("ee.api.v1.auth.AuthService")
    def test_service_error(self, mock_service_cls, public_client):
        mock_service_cls.return_value.verify_user_email.side_effect = Exception("err")
        resp = public_client.get(
            "/api/v1/auth/verify_user_email",
            params={"email": "user@example.com", "code": "123456", "user_id": 1},
        )
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# POST /api/v1/auth/login
# ---------------------------------------------------------------------------

class TestLogin:
    """Tests for POST /api/v1/auth/login"""

    @patch("ee.api.v1.auth.AuthService")
    def test_success(self, mock_service_cls, public_client, login_payload):
        mock_service_cls.return_value.login.return_value = {"token": "jwt-token"}
        resp = public_client.post("/api/v1/auth/login", json=login_payload)
        assert resp.status_code == 200
        assert "token" in resp.json()
        mock_service_cls.return_value.login.assert_called_once_with(
            "user@example.com", "SecurePass123!",
        )

    def test_missing_email(self, public_client):
        resp = public_client.post("/api/v1/auth/login", json={"password": "pass"})
        assert resp.status_code == 400

    def test_missing_password(self, public_client):
        resp = public_client.post("/api/v1/auth/login", json={"email": "user@example.com"})
        assert resp.status_code == 400

    def test_missing_both(self, public_client):
        resp = public_client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 400

    @patch("ee.api.v1.auth.AuthService")
    def test_invalid_credentials(self, mock_service_cls, public_client, login_payload):
        mock_service_cls.return_value.login.side_effect = HTTPException(
            status_code=401, detail="Invalid credentials"
        )
        resp = public_client.post("/api/v1/auth/login", json=login_payload)
        assert resp.status_code == 401

    @patch("ee.api.v1.auth.AuthService")
    def test_service_error(self, mock_service_cls, public_client, login_payload):
        mock_service_cls.return_value.login.side_effect = HTTPException(status_code=500, detail="DB error")
        resp = public_client.post("/api/v1/auth/login", json=login_payload)
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/auth/forget-password
# ---------------------------------------------------------------------------

class TestForgetPassword:
    """Tests for GET /api/v1/auth/forget-password"""

    @patch("ee.api.v1.auth.AuthService")
    def test_success(self, mock_service_cls, public_client):
        mock_service_cls.return_value.forgot_password.return_value = {"message": "Email sent"}
        resp = public_client.get(
            "/api/v1/auth/forget-password", params={"email": "user@example.com"}
        )
        assert resp.status_code == 200
        mock_service_cls.return_value.forgot_password.assert_called_once_with("user@example.com")

    def test_missing_email(self, public_client):
        resp = public_client.get("/api/v1/auth/forget-password")
        assert resp.status_code == 422

    @patch("ee.api.v1.auth.AuthService")
    def test_service_error(self, mock_service_cls, public_client):
        mock_service_cls.return_value.forgot_password.side_effect = Exception("err")
        resp = public_client.get(
            "/api/v1/auth/forget-password", params={"email": "user@example.com"}
        )
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/auth/acceptForgotPassword
# ---------------------------------------------------------------------------

class TestAcceptForgotPassword:
    """Tests for GET /api/v1/auth/acceptForgotPassword"""

    @patch("ee.api.v1.auth.AuthService")
    def test_success(self, mock_service_cls, public_client):
        mock_service_cls.return_value.accept_forgot_password.return_value = {
            "message": "Password reset"
        }
        resp = public_client.get(
            "/api/v1/auth/acceptForgotPassword",
            params={"email": "user@example.com", "password": "NewPass!", "token": "reset-tok"},
        )
        assert resp.status_code == 200
        mock_service_cls.return_value.accept_forgot_password.assert_called_once_with(
            "user@example.com", "NewPass!", "reset-tok",
        )

    def test_missing_email(self, public_client):
        resp = public_client.get(
            "/api/v1/auth/acceptForgotPassword",
            params={"password": "p", "token": "t"},
        )
        assert resp.status_code == 422

    def test_missing_password(self, public_client):
        resp = public_client.get(
            "/api/v1/auth/acceptForgotPassword",
            params={"email": "a@b.com", "token": "t"},
        )
        assert resp.status_code == 422

    def test_missing_token(self, public_client):
        resp = public_client.get(
            "/api/v1/auth/acceptForgotPassword",
            params={"email": "a@b.com", "password": "p"},
        )
        assert resp.status_code == 422

    @patch("ee.api.v1.auth.AuthService")
    def test_service_error(self, mock_service_cls, public_client):
        mock_service_cls.return_value.accept_forgot_password.side_effect = Exception("err")
        resp = public_client.get(
            "/api/v1/auth/acceptForgotPassword",
            params={"email": "a@b.com", "password": "p", "token": "t"},
        )
        assert resp.status_code in (500, 422, 400)
