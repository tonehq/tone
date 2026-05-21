"""Tests for Auth API endpoints (Core edition).

Source: core/api/v1/auth.py
Postman collection: postman_collection/auth.postman_collection.json
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
        "email": "user@example.com",
        "password": "securePassword123",
        "username": "johndoe",
        "profile": {
            "first_name": "John",
            "last_name": "Doe",
        },
    }


@pytest.fixture
def login_payload():
    return {"email": "user@example.com", "password": "securePassword123"}


# ---------------------------------------------------------------------------
# POST /api/v1/auth/signup
# ---------------------------------------------------------------------------

class TestSignup:
    """Tests for POST /api/v1/auth/signup"""

    @patch("ee.api.v1.auth.AuthService")
    def test_signup_success(self, mock_service_cls, public_client, signup_payload):
        """Postman: Signup - Success (201)"""
        mock_service_cls.return_value.signup.return_value = {
            "user_id": 1,
            "email": "user@example.com",
            "username": "johndoe",
            "status": "pending",
            "message": "User created successfully. Please verify your email.",
        }
        resp = public_client.post("/api/v1/auth/signup", json=signup_payload)
        assert resp.status_code == 201
        mock_service_cls.return_value.signup.assert_called_once_with(
            "user@example.com",
            "securePassword123",
            "johndoe",
            {"first_name": "John", "last_name": "Doe"},
        )

    @patch("ee.api.v1.auth.AuthService")
    def test_signup_success_without_username(self, mock_service_cls, public_client):
        mock_service_cls.return_value.signup.return_value = {
            "user_id": 1,
            "email": "a@b.com",
            "status": "pending",
        }
        resp = public_client.post(
            "/api/v1/auth/signup",
            json={"email": "a@b.com", "password": "pass123"},
        )
        assert resp.status_code == 201
        mock_service_cls.return_value.signup.assert_called_once_with(
            "a@b.com", "pass123", None, {},
        )

    def test_signup_missing_fields(self, public_client):
        """Postman: Signup - Missing Fields (400)"""
        resp = public_client.post(
            "/api/v1/auth/signup",
            json={"email": "user@example.com"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Email and password are required"

    def test_signup_missing_email(self, public_client):
        resp = public_client.post("/api/v1/auth/signup", json={"password": "pass123"})
        assert resp.status_code == 400

    def test_signup_missing_both(self, public_client):
        resp = public_client.post("/api/v1/auth/signup", json={})
        assert resp.status_code == 400

    @patch("ee.api.v1.auth.AuthService")
    def test_signup_duplicate_email(self, mock_service_cls, public_client, signup_payload):
        """Postman: Signup - Duplicate Email (400)"""
        mock_service_cls.return_value.signup.side_effect = HTTPException(
            status_code=400, detail="User with this email already exists"
        )
        resp = public_client.post("/api/v1/auth/signup", json=signup_payload)
        assert resp.status_code == 400
        assert resp.json()["detail"] == "User with this email already exists"

    @patch("ee.api.v1.auth.AuthService")
    def test_signup_username_taken(self, mock_service_cls, public_client):
        """Postman: Signup - Username Taken (400)"""
        mock_service_cls.return_value.signup.side_effect = HTTPException(
            status_code=400, detail="Username already taken"
        )
        resp = public_client.post(
            "/api/v1/auth/signup",
            json={
                "email": "newuser@example.com",
                "password": "securePassword123",
                "username": "existinguser",
            },
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Username already taken"

    @patch("ee.api.v1.auth.AuthService")
    def test_signup_service_error(self, mock_service_cls, public_client, signup_payload):
        mock_service_cls.return_value.signup.side_effect = HTTPException(status_code=500, detail="DB error")
        resp = public_client.post("/api/v1/auth/signup", json=signup_payload)
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# POST /api/v1/auth/signup_with_firebase
# ---------------------------------------------------------------------------

class TestSignupWithFirebase:
    """Tests for POST /api/v1/auth/signup_with_firebase"""

    @patch("ee.api.v1.auth.AuthService")
    def test_signup_with_firebase_success(self, mock_service_cls, public_client):
        """Postman: Signup With Firebase - Success (201)"""
        mock_service_cls.return_value.signup_with_firebase.return_value = {
            "user_id": 1,
            "email": "user@example.com",
            "status": "active",
            "message": "User authenticated with Firebase successfully",
        }
        resp = public_client.post(
            "/api/v1/auth/signup_with_firebase",
            json={
                "email": "user@example.com",
                "profile": {"first_name": "John", "last_name": "Doe"},
            },
            headers={"Authorization": "Bearer firebase-token-123"},
        )
        assert resp.status_code == 201
        mock_service_cls.return_value.signup_with_firebase.assert_called_once_with(
            "firebase-token-123",
            "user@example.com",
            {"first_name": "John", "last_name": "Doe"},
        )

    def test_signup_with_firebase_missing_email(self, public_client):
        """Postman: Signup With Firebase - Missing Email (400)"""
        resp = public_client.post(
            "/api/v1/auth/signup_with_firebase",
            json={"profile": {}},
            headers={"Authorization": "Bearer token"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Email is required"

    def test_signup_with_firebase_invalid_authorization_header(self, public_client):
        """Postman: Signup With Firebase - Invalid Authorization Header (401)"""
        resp = public_client.post(
            "/api/v1/auth/signup_with_firebase",
            json={"email": "user@example.com"},
            headers={"Authorization": "InvalidToken"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid authorization header"

    def test_signup_with_firebase_missing_authorization_header(self, public_client):
        resp = public_client.post(
            "/api/v1/auth/signup_with_firebase",
            json={"email": "user@example.com"},
        )
        assert resp.status_code == 422

    @patch("ee.api.v1.auth.AuthService")
    def test_signup_with_firebase_service_error(self, mock_service_cls, public_client):
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
    def test_resend_verification_email_success(self, mock_service_cls, public_client):
        """Postman: Resend Verification Email - Success (200)"""
        mock_service_cls.return_value.resend_verification_email.return_value = {
            "message": "Verification email sent successfully"
        }
        resp = public_client.get(
            "/api/v1/auth/resend_verification_email", params={"email": "user@example.com"}
        )
        assert resp.status_code == 200

    @patch("ee.api.v1.auth.AuthService")
    def test_resend_verification_email_user_not_found(self, mock_service_cls, public_client):
        """Postman: Resend Verification Email - User Not Found (404)"""
        mock_service_cls.return_value.resend_verification_email.side_effect = HTTPException(
            status_code=404, detail="User not found"
        )
        resp = public_client.get(
            "/api/v1/auth/resend_verification_email",
            params={"email": "nonexistent@example.com"},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "User not found"

    @patch("ee.api.v1.auth.AuthService")
    def test_resend_verification_email_already_verified(self, mock_service_cls, public_client):
        """Postman: Resend Verification Email - Already Verified (400)"""
        mock_service_cls.return_value.resend_verification_email.side_effect = HTTPException(
            status_code=400, detail="Email already verified"
        )
        resp = public_client.get(
            "/api/v1/auth/resend_verification_email",
            params={"email": "verified@example.com"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Email already verified"

    def test_resend_verification_email_missing_email(self, public_client):
        resp = public_client.get("/api/v1/auth/resend_verification_email")
        assert resp.status_code == 422

    @patch("ee.api.v1.auth.AuthService")
    def test_resend_verification_email_service_error(self, mock_service_cls, public_client):
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
    def test_verify_user_email_success(self, mock_service_cls, public_client):
        """Postman: Verify User Email - Success (200)"""
        mock_service_cls.return_value.verify_user_email.return_value = {
            "message": "Email verified successfully"
        }
        resp = public_client.get(
            "/api/v1/auth/verify_user_email",
            params={"email": "user@example.com", "code": "123456", "user_id": 1},
        )
        assert resp.status_code == 200
        mock_service_cls.return_value.verify_user_email.assert_called_once_with(
            "user@example.com", "123456", 1,
        )

    @patch("ee.api.v1.auth.AuthService")
    def test_verify_user_email_invalid_or_expired_code(self, mock_service_cls, public_client):
        """Postman: Verify User Email - Invalid Or Expired Code (400)"""
        mock_service_cls.return_value.verify_user_email.side_effect = HTTPException(
            status_code=400, detail="Invalid or expired verification code"
        )
        resp = public_client.get(
            "/api/v1/auth/verify_user_email",
            params={"email": "user@example.com", "code": "000000", "user_id": 1},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid or expired verification code"

    @patch("ee.api.v1.auth.AuthService")
    def test_verify_user_email_max_attempts_exceeded(self, mock_service_cls, public_client):
        """Postman: Verify User Email - Max Attempts Exceeded (400)"""
        mock_service_cls.return_value.verify_user_email.side_effect = HTTPException(
            status_code=400, detail="Maximum verification attempts exceeded"
        )
        resp = public_client.get(
            "/api/v1/auth/verify_user_email",
            params={"email": "user@example.com", "code": "123456", "user_id": 1},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Maximum verification attempts exceeded"

    def test_verify_user_email_missing_email(self, public_client):
        resp = public_client.get(
            "/api/v1/auth/verify_user_email",
            params={"code": "123456", "user_id": 1},
        )
        assert resp.status_code == 422

    def test_verify_user_email_missing_code(self, public_client):
        resp = public_client.get(
            "/api/v1/auth/verify_user_email",
            params={"email": "user@example.com", "user_id": 1},
        )
        assert resp.status_code == 422

    def test_verify_user_email_missing_user_id(self, public_client):
        resp = public_client.get(
            "/api/v1/auth/verify_user_email",
            params={"email": "user@example.com", "code": "123456"},
        )
        assert resp.status_code == 422

    @patch("ee.api.v1.auth.AuthService")
    def test_verify_user_email_service_error(self, mock_service_cls, public_client):
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
    def test_login_success(self, mock_service_cls, public_client, login_payload):
        """Postman: Login - Success (200)"""
        mock_service_cls.return_value.login.return_value = {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "user_id": 1,
            "email": "user@example.com",
            "org_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
            "role": "owner",
        }
        resp = public_client.post("/api/v1/auth/login", json=login_payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        mock_service_cls.return_value.login.assert_called_once_with(
            "user@example.com", "securePassword123",
        )

    def test_login_missing_fields(self, public_client):
        """Postman: Login - Missing Fields (400)"""
        resp = public_client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Email and password are required"

    def test_login_missing_email(self, public_client):
        resp = public_client.post("/api/v1/auth/login", json={"password": "pass"})
        assert resp.status_code == 400

    def test_login_missing_both(self, public_client):
        resp = public_client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 400

    @patch("ee.api.v1.auth.AuthService")
    def test_login_invalid_credentials(self, mock_service_cls, public_client, login_payload):
        """Postman: Login - Invalid Credentials (401)"""
        mock_service_cls.return_value.login.side_effect = HTTPException(
            status_code=401, detail="Invalid email or password"
        )
        resp = public_client.post("/api/v1/auth/login", json=login_payload)
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid email or password"

    @patch("ee.api.v1.auth.AuthService")
    def test_login_account_not_active(self, mock_service_cls, public_client):
        """Postman: Login - Account Not Active (401)"""
        mock_service_cls.return_value.login.side_effect = HTTPException(
            status_code=401, detail="Account not active. Please verify your email."
        )
        resp = public_client.post(
            "/api/v1/auth/login",
            json={"email": "unverified@example.com", "password": "securePassword123"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Account not active. Please verify your email."

    @patch("ee.api.v1.auth.AuthService")
    def test_login_service_error(self, mock_service_cls, public_client, login_payload):
        mock_service_cls.return_value.login.side_effect = HTTPException(status_code=500, detail="DB error")
        resp = public_client.post("/api/v1/auth/login", json=login_payload)
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# GET /api/v1/auth/forget-password
# ---------------------------------------------------------------------------

class TestForgetPassword:
    """Tests for GET /api/v1/auth/forget-password"""

    @patch("ee.api.v1.auth.AuthService")
    def test_forget_password_success(self, mock_service_cls, public_client):
        """Postman: Forget Password - Success (200)"""
        mock_service_cls.return_value.forgot_password.return_value = {
            "message": "If the email exists, you will receive a password reset link"
        }
        resp = public_client.get(
            "/api/v1/auth/forget-password", params={"email": "user@example.com"}
        )
        assert resp.status_code == 200
        mock_service_cls.return_value.forgot_password.assert_called_once_with("user@example.com")

    def test_forget_password_missing_email(self, public_client):
        resp = public_client.get("/api/v1/auth/forget-password")
        assert resp.status_code == 422

    @patch("ee.api.v1.auth.AuthService")
    def test_forget_password_service_error(self, mock_service_cls, public_client):
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
    def test_accept_forgot_password_success(self, mock_service_cls, public_client):
        """Postman: Accept Forgot Password - Success (200)"""
        mock_service_cls.return_value.accept_forgot_password.return_value = {
            "message": "Password reset successfully"
        }
        resp = public_client.get(
            "/api/v1/auth/acceptForgotPassword",
            params={
                "email": "user@example.com",
                "password": "newPassword123",
                "token": "reset-token-here",
            },
        )
        assert resp.status_code == 200
        mock_service_cls.return_value.accept_forgot_password.assert_called_once_with(
            "user@example.com", "newPassword123", "reset-token-here",
        )

    @patch("ee.api.v1.auth.AuthService")
    def test_accept_forgot_password_invalid_or_expired_token(self, mock_service_cls, public_client):
        """Postman: Accept Forgot Password - Invalid Or Expired Token (400)"""
        mock_service_cls.return_value.accept_forgot_password.side_effect = HTTPException(
            status_code=400, detail="Invalid or expired reset token"
        )
        resp = public_client.get(
            "/api/v1/auth/acceptForgotPassword",
            params={
                "email": "user@example.com",
                "password": "newPassword123",
                "token": "invalid-token",
            },
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid or expired reset token"

    @patch("ee.api.v1.auth.AuthService")
    def test_accept_forgot_password_user_not_found(self, mock_service_cls, public_client):
        """Postman: Accept Forgot Password - User Not Found (404)"""
        mock_service_cls.return_value.accept_forgot_password.side_effect = HTTPException(
            status_code=404, detail="User not found"
        )
        resp = public_client.get(
            "/api/v1/auth/acceptForgotPassword",
            params={
                "email": "deleted@example.com",
                "password": "newPassword123",
                "token": "valid-token",
            },
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "User not found"

    def test_accept_forgot_password_missing_email(self, public_client):
        resp = public_client.get(
            "/api/v1/auth/acceptForgotPassword",
            params={"password": "p", "token": "t"},
        )
        assert resp.status_code == 422

    def test_accept_forgot_password_missing_password(self, public_client):
        resp = public_client.get(
            "/api/v1/auth/acceptForgotPassword",
            params={"email": "a@b.com", "token": "t"},
        )
        assert resp.status_code == 422

    def test_accept_forgot_password_missing_token(self, public_client):
        resp = public_client.get(
            "/api/v1/auth/acceptForgotPassword",
            params={"email": "a@b.com", "password": "p"},
        )
        assert resp.status_code == 422

    @patch("ee.api.v1.auth.AuthService")
    def test_accept_forgot_password_service_error(self, mock_service_cls, public_client):
        mock_service_cls.return_value.accept_forgot_password.side_effect = Exception("err")
        resp = public_client.get(
            "/api/v1/auth/acceptForgotPassword",
            params={"email": "a@b.com", "password": "p", "token": "t"},
        )
        assert resp.status_code in (500, 422, 400)


# ---------------------------------------------------------------------------
# [EE] GET /api/v1/auth/check_organization_exists
# ---------------------------------------------------------------------------

class TestCheckOrganizationExists:
    """Tests for GET /api/v1/auth/check_organization_exists (EE endpoint)"""

    @patch("ee.api.v1.auth.AuthService")
    def test_check_organization_exists_found(self, mock_service_cls, public_client):
        """Postman: [EE] Check Organization Exists - Found (200)"""
        mock_service_cls.return_value.check_organization_exists.return_value = {
            "exists": True,
            "organization": {
                "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "name": "My Organization",
            },
        }
        resp = public_client.get(
            "/api/v1/auth/check_organization_exists",
            params={"name": "My Organization"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["exists"] is True

    @patch("ee.api.v1.auth.AuthService")
    def test_check_organization_exists_not_found(self, mock_service_cls, public_client):
        """Postman: [EE] Check Organization Exists - Not Found (200)"""
        mock_service_cls.return_value.check_organization_exists.return_value = {
            "exists": False,
        }
        resp = public_client.get(
            "/api/v1/auth/check_organization_exists",
            params={"name": "Nonexistent Org"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["exists"] is False


# ---------------------------------------------------------------------------
# [EE] POST /api/v1/auth/switch_organization
# ---------------------------------------------------------------------------

class TestSwitchOrganization:
    """Tests for POST /api/v1/auth/switch_organization (EE endpoint)"""

    @patch("ee.api.v1.auth.AuthService")
    def test_switch_organization_success(self, mock_service_cls, client_as_member):
        """Postman: [EE] Switch Organization - Success (200)"""
        mock_service_cls.return_value.switch_organization.return_value = {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "organization": {
                "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "name": "My Organization",
                "role": "owner",
            },
        }
        resp = client_as_member.post(
            "/api/v1/auth/switch_organization",
            json={"organization_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    @patch("ee.api.v1.auth.AuthService")
    def test_switch_organization_missing_org_id(self, mock_service_cls, client_as_member):
        """Postman: [EE] Switch Organization - Missing Organization ID (400)"""
        mock_service_cls.return_value.switch_organization.side_effect = HTTPException(
            status_code=400, detail="Organization ID is required"
        )
        resp = client_as_member.post(
            "/api/v1/auth/switch_organization",
            json={},
        )
        assert resp.status_code == 400
