"""Tests for Auth API endpoints.

Source: core/api/v1/auth.py
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException


# ─── POST /api/v1/auth/signup — Signup ───

class TestSignup:
    """Tests for POST /api/v1/auth/signup"""

    @patch("ee.api.v1.auth.EEAuthService")
    def test_signup_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.signup.return_value = {
            "id": 1, "email": "new@example.com", "token": "jwt-token"
        }
        response = client_as_member.post("/api/v1/auth/signup", json={
            "email": "new@example.com",
            "password": "securepass123",
            "username": "newuser"
        })
        assert response.status_code == 201

    @patch("ee.api.v1.auth.EEAuthService")
    def test_signup_with_profile(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.signup.return_value = {"id": 1}
        response = client_as_member.post("/api/v1/auth/signup", json={
            "email": "new@example.com",
            "password": "pass123",
            "profile": {"first_name": "Test"}
        })
        assert response.status_code == 201

    @patch("ee.api.v1.auth.EEAuthService")
    def test_signup_missing_email(self, mock_service_cls, client_as_member):
        response = client_as_member.post("/api/v1/auth/signup", json={
            "password": "pass123"
        })
        assert response.status_code == 400
        assert "Email and password are required" in response.json()["detail"]

    @patch("ee.api.v1.auth.EEAuthService")
    def test_signup_missing_password(self, mock_service_cls, client_as_member):
        response = client_as_member.post("/api/v1/auth/signup", json={
            "email": "new@example.com"
        })
        assert response.status_code == 400

    @patch("ee.api.v1.auth.EEAuthService")
    def test_signup_missing_both_email_and_password(self, mock_service_cls, client_as_member):
        response = client_as_member.post("/api/v1/auth/signup", json={})
        assert response.status_code == 400

    @patch("ee.api.v1.auth.EEAuthService")
    def test_signup_empty_body(self, mock_service_cls, client_as_member):
        response = client_as_member.post("/api/v1/auth/signup", json={})
        assert response.status_code == 400

    @patch("ee.api.v1.auth.EEAuthService")
    def test_signup_service_raises_conflict(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.signup.side_effect = HTTPException(
            status_code=409, detail="Email already exists"
        )
        response = client_as_member.post("/api/v1/auth/signup", json={
            "email": "existing@example.com",
            "password": "pass123"
        })
        assert response.status_code == 409


# ─── POST /api/v1/auth/signup_with_firebase — Signup with Firebase ───

class TestSignupWithFirebase:
    """Tests for POST /api/v1/auth/signup_with_firebase"""

    @patch("ee.api.v1.auth.EEAuthService")
    def test_signup_with_firebase_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.signup_with_firebase.return_value = {"id": 1}
        response = client_as_member.post(
            "/api/v1/auth/signup_with_firebase",
            json={"email": "fb@example.com", "profile": {}},
            headers={"Authorization": "Bearer firebase-token-123"}
        )
        assert response.status_code == 201

    @patch("ee.api.v1.auth.EEAuthService")
    def test_signup_with_firebase_missing_email(self, mock_service_cls, client_as_member):
        response = client_as_member.post(
            "/api/v1/auth/signup_with_firebase",
            json={"profile": {}},
            headers={"Authorization": "Bearer firebase-token-123"}
        )
        assert response.status_code == 400
        assert "Email is required" in response.json()["detail"]

    @patch("ee.api.v1.auth.EEAuthService")
    def test_signup_with_firebase_invalid_auth_header(self, mock_service_cls, client_as_member):
        response = client_as_member.post(
            "/api/v1/auth/signup_with_firebase",
            json={"email": "fb@example.com"},
            headers={"Authorization": "InvalidFormat token"}
        )
        assert response.status_code == 401

    def test_signup_with_firebase_no_auth_header(self, client_as_member):
        response = client_as_member.post(
            "/api/v1/auth/signup_with_firebase",
            json={"email": "fb@example.com"}
        )
        assert response.status_code == 422


# ─── GET /api/v1/auth/resend_verification_email — Resend Verification ───

class TestResendVerificationEmail:
    """Tests for GET /api/v1/auth/resend_verification_email"""

    @patch("ee.api.v1.auth.EEAuthService")
    def test_resend_verification_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.resend_verification_email.return_value = {"message": "sent"}
        response = client_as_member.get("/api/v1/auth/resend_verification_email?email=test@example.com")
        assert response.status_code == 200

    def test_resend_verification_missing_email(self, client_as_member):
        response = client_as_member.get("/api/v1/auth/resend_verification_email")
        assert response.status_code == 422


# ─── GET /api/v1/auth/verify_user_email — Verify User Email ───

class TestVerifyUserEmail:
    """Tests for GET /api/v1/auth/verify_user_email"""

    @patch("ee.api.v1.auth.EEAuthService")
    def test_verify_email_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.verify_user_email.return_value = {"verified": True}
        response = client_as_member.get(
            "/api/v1/auth/verify_user_email?email=test@example.com&code=123456&user_id=1"
        )
        assert response.status_code == 200

    def test_verify_email_missing_code(self, client_as_member):
        response = client_as_member.get(
            "/api/v1/auth/verify_user_email?email=test@example.com&user_id=1"
        )
        assert response.status_code == 422

    def test_verify_email_missing_email(self, client_as_member):
        response = client_as_member.get(
            "/api/v1/auth/verify_user_email?code=123456&user_id=1"
        )
        assert response.status_code == 422

    def test_verify_email_missing_user_id(self, client_as_member):
        response = client_as_member.get(
            "/api/v1/auth/verify_user_email?email=test@example.com&code=123456"
        )
        assert response.status_code == 422

    def test_verify_email_invalid_user_id_type(self, client_as_member):
        response = client_as_member.get(
            "/api/v1/auth/verify_user_email?email=test@example.com&code=123456&user_id=abc"
        )
        assert response.status_code == 422


# ─── POST /api/v1/auth/login — Login ───

class TestLogin:
    """Tests for POST /api/v1/auth/login"""

    @patch("ee.api.v1.auth.EEAuthService")
    def test_login_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.login.return_value = {"token": "jwt-token"}
        response = client_as_member.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "pass123"
        })
        assert response.status_code == 200

    @patch("ee.api.v1.auth.EEAuthService")
    def test_login_missing_email(self, mock_service_cls, client_as_member):
        response = client_as_member.post("/api/v1/auth/login", json={
            "password": "pass123"
        })
        assert response.status_code == 400

    @patch("ee.api.v1.auth.EEAuthService")
    def test_login_missing_password(self, mock_service_cls, client_as_member):
        response = client_as_member.post("/api/v1/auth/login", json={
            "email": "test@example.com"
        })
        assert response.status_code == 400

    @patch("ee.api.v1.auth.EEAuthService")
    def test_login_empty_body(self, mock_service_cls, client_as_member):
        response = client_as_member.post("/api/v1/auth/login", json={})
        assert response.status_code == 400

    @patch("ee.api.v1.auth.EEAuthService")
    def test_login_invalid_credentials(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.login.side_effect = HTTPException(
            status_code=401, detail="Invalid credentials"
        )
        response = client_as_member.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "wrong"
        })
        assert response.status_code == 401


# ─── GET /api/v1/auth/forget-password — Forgot Password ───

class TestForgotPassword:
    """Tests for GET /api/v1/auth/forget-password"""

    @patch("ee.api.v1.auth.EEAuthService")
    def test_forgot_password_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.forgot_password.return_value = {"message": "sent"}
        response = client_as_member.get("/api/v1/auth/forget-password?email=test@example.com")
        assert response.status_code == 200

    def test_forgot_password_missing_email(self, client_as_member):
        response = client_as_member.get("/api/v1/auth/forget-password")
        assert response.status_code == 422

    @patch("ee.api.v1.auth.EEAuthService")
    def test_forgot_password_nonexistent_email(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.forgot_password.side_effect = HTTPException(
            status_code=404, detail="User not found"
        )
        response = client_as_member.get("/api/v1/auth/forget-password?email=none@example.com")
        assert response.status_code == 404


# ─── GET /api/v1/auth/acceptForgotPassword — Accept Forgot Password ───

class TestAcceptForgotPassword:
    """Tests for GET /api/v1/auth/acceptForgotPassword"""

    @patch("ee.api.v1.auth.EEAuthService")
    def test_accept_forgot_password_success(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.accept_forgot_password.return_value = {"message": "reset"}
        response = client_as_member.get(
            "/api/v1/auth/acceptForgotPassword?email=test@example.com&password=newpass&token=reset-token"
        )
        assert response.status_code == 200

    def test_accept_forgot_password_missing_email(self, client_as_member):
        response = client_as_member.get(
            "/api/v1/auth/acceptForgotPassword?password=newpass&token=reset-token"
        )
        assert response.status_code == 422

    def test_accept_forgot_password_missing_password(self, client_as_member):
        response = client_as_member.get(
            "/api/v1/auth/acceptForgotPassword?email=test@example.com&token=reset-token"
        )
        assert response.status_code == 422

    def test_accept_forgot_password_missing_token(self, client_as_member):
        response = client_as_member.get(
            "/api/v1/auth/acceptForgotPassword?email=test@example.com&password=newpass"
        )
        assert response.status_code == 422

    @patch("ee.api.v1.auth.EEAuthService")
    def test_accept_forgot_password_invalid_token(self, mock_service_cls, client_as_member):
        mock_service_cls.return_value.accept_forgot_password.side_effect = HTTPException(
            status_code=400, detail="Invalid or expired token"
        )
        response = client_as_member.get(
            "/api/v1/auth/acceptForgotPassword?email=test@example.com&password=new&token=bad"
        )
        assert response.status_code == 400
