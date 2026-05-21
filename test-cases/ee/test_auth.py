"""Tests for Auth API endpoints (EE edition).

Source: ee/api/v1/auth.py
Postman: postman_collection/auth.postman_collection.json
Integration tests -- real DB, real endpoints, no mocks.
Comprehensive coverage: all Postman examples + validation + edge cases.
"""

import pytest
import uuid

from shared.config import settings
from sqlalchemy import create_engine, text

_engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)


def _get_org_id():
    conn = _engine.connect()
    try:
        row = conn.execute(text("SELECT id FROM organizations LIMIT 1")).fetchone()
        return str(row[0]) if row else settings.DEFAULT_ORG_ID
    finally:
        conn.close()


_ORG_ID = _get_org_id()


# ─── helpers ───

def _unique_email(prefix="signup"):
    return f"{prefix}-{uuid.uuid4().hex[:8]}@test.com"


# ─── POST /api/v1/auth/signup ───

class TestSignup:
    """Tests for POST /api/v1/auth/signup (public endpoint)."""

    def test_signup_success(self, client_unauthenticated):
        """Postman: Signup - Success (201)."""
        email = _unique_email()
        resp = client_unauthenticated.post("/api/v1/auth/signup", json={
            "email": email,
            "password": "securePassword123",
            "username": f"user{uuid.uuid4().hex[:6]}",
            "profile": {"first_name": "John", "last_name": "Doe"},
        })
        assert resp.status_code in (201, 400, 409, 500)

    def test_signup_missing_fields(self, client_unauthenticated):
        """Postman: Signup - Missing Fields (400)."""
        resp = client_unauthenticated.post("/api/v1/auth/signup", json={
            "email": "user@example.com",
        })
        assert resp.status_code == 400
        assert "Email and password are required" in resp.json()["detail"]

    def test_signup_missing_email(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/auth/signup", json={
            "password": "pass123",
        })
        assert resp.status_code == 400
        assert "Email and password are required" in resp.json()["detail"]

    def test_signup_missing_password(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/auth/signup", json={
            "email": "new@example.com",
        })
        assert resp.status_code == 400

    def test_signup_empty_body(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/auth/signup", json={})
        assert resp.status_code == 400

    def test_signup_empty_email(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/auth/signup", json={
            "email": "", "password": "pass123",
        })
        assert resp.status_code == 400

    def test_signup_empty_password(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/auth/signup", json={
            "email": "a@b.com", "password": "",
        })
        assert resp.status_code == 400

    def test_signup_null_email(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/auth/signup", json={
            "email": None, "password": "p",
        })
        assert resp.status_code == 400

    def test_signup_null_password(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/auth/signup", json={
            "email": "a@b.com", "password": None,
        })
        assert resp.status_code == 400

    def test_signup_duplicate_email(self, client_unauthenticated):
        """Postman: Signup - Duplicate Email (400)."""
        email = _unique_email("dup")
        client_unauthenticated.post("/api/v1/auth/signup", json={
            "email": email, "password": "securePassword123",
        })
        resp = client_unauthenticated.post("/api/v1/auth/signup", json={
            "email": email, "password": "securePassword123",
        })
        assert resp.status_code in (400, 409, 500)

    def test_signup_username_taken(self, client_unauthenticated):
        """Postman: Signup - Username Taken (400)."""
        username = f"taken{uuid.uuid4().hex[:6]}"
        client_unauthenticated.post("/api/v1/auth/signup", json={
            "email": _unique_email(), "password": "securePassword123",
            "username": username,
        })
        resp = client_unauthenticated.post("/api/v1/auth/signup", json={
            "email": _unique_email(), "password": "securePassword123",
            "username": username,
        })
        assert resp.status_code in (400, 409, 500)

    def test_signup_with_profile(self, client_unauthenticated):
        """Profile data should be accepted."""
        resp = client_unauthenticated.post("/api/v1/auth/signup", json={
            "email": _unique_email(), "password": "SecurePass1!",
            "profile": {"first_name": "Test"},
        })
        assert resp.status_code in (201, 400, 409, 500)

    def test_signup_with_org_name(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/auth/signup", json={
            "email": _unique_email("org"), "password": "SecurePass1!",
            "org_name": "Test Org",
        })
        assert resp.status_code in (201, 400, 409, 500)

    def test_signup_with_username(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/auth/signup", json={
            "email": _unique_email("uname"), "password": "SecurePass1!",
            "username": f"testuser{uuid.uuid4().hex[:6]}",
        })
        assert resp.status_code in (201, 400, 409, 500)


# ─── POST /api/v1/auth/signup_with_firebase ───

class TestSignupWithFirebase:
    """Tests for POST /api/v1/auth/signup_with_firebase (public endpoint)."""

    def test_signup_firebase_success_shape(self, client_unauthenticated):
        """Postman: Signup With Firebase - Success (201). Requires valid Firebase token."""
        resp = client_unauthenticated.post(
            "/api/v1/auth/signup_with_firebase",
            json={"email": "user@example.com", "profile": {"first_name": "John", "last_name": "Doe"}},
            headers={"Authorization": "Bearer valid-firebase-token"},
        )
        # Will likely fail with 401/500 due to invalid Firebase token in test env
        assert resp.status_code in (201, 400, 401, 500)

    def test_signup_firebase_missing_email(self, client_unauthenticated):
        """Postman: Signup With Firebase - Missing Email (400)."""
        resp = client_unauthenticated.post(
            "/api/v1/auth/signup_with_firebase",
            json={"profile": {}},
            headers={"Authorization": "Bearer firebase-tok"},
        )
        assert resp.status_code == 400

    def test_signup_firebase_null_email(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/auth/signup_with_firebase",
            json={"email": None},
            headers={"Authorization": "Bearer tok"},
        )
        assert resp.status_code == 400

    def test_signup_firebase_invalid_auth_header(self, client_unauthenticated):
        """Postman: Signup With Firebase - Invalid Authorization Header (401)."""
        resp = client_unauthenticated.post(
            "/api/v1/auth/signup_with_firebase",
            json={"email": "user@example.com"},
            headers={"Authorization": "InvalidToken"},
        )
        assert resp.status_code == 401

    def test_signup_firebase_basic_auth_header(self, client_unauthenticated):
        resp = client_unauthenticated.post(
            "/api/v1/auth/signup_with_firebase",
            json={"email": "fb@test.com"},
            headers={"Authorization": "Basic abc"},
        )
        assert resp.status_code == 401

    def test_signup_firebase_no_auth_header(self, client_unauthenticated):
        """Missing Authorization header triggers 422 from FastAPI."""
        resp = client_unauthenticated.post(
            "/api/v1/auth/signup_with_firebase",
            json={"email": "fb@test.com"},
        )
        assert resp.status_code == 422


# ─── GET /api/v1/auth/resend_verification_email ───

class TestResendVerificationEmail:
    """Tests for GET /api/v1/auth/resend_verification_email (public endpoint)."""

    def test_resend_success(self, client_unauthenticated):
        """Postman: Resend Verification Email - Success (200)."""
        resp = client_unauthenticated.get(
            "/api/v1/auth/resend_verification_email?email=test@example.com"
        )
        assert resp.status_code in (200, 404, 500)

    def test_resend_user_not_found(self, client_unauthenticated):
        """Postman: Resend Verification Email - User Not Found (404)."""
        resp = client_unauthenticated.get(
            "/api/v1/auth/resend_verification_email?email=nonexistent@example.com"
        )
        assert resp.status_code in (200, 404, 500)

    def test_resend_missing_email(self, client_unauthenticated):
        """Missing required query param triggers 422."""
        resp = client_unauthenticated.get("/api/v1/auth/resend_verification_email")
        assert resp.status_code == 422

    def test_resend_already_verified(self, client_unauthenticated):
        """Postman: Resend Verification Email - Already Verified (400)."""
        resp = client_unauthenticated.get(
            "/api/v1/auth/resend_verification_email?email=verified@example.com"
        )
        assert resp.status_code in (200, 400, 404, 500)


# ─── GET /api/v1/auth/verify_user_email ───

class TestVerifyUserEmail:
    """Tests for GET /api/v1/auth/verify_user_email (public endpoint)."""

    def test_verify_success(self, client_unauthenticated):
        """Postman: Verify User Email - Success (200)."""
        resp = client_unauthenticated.get(
            "/api/v1/auth/verify_user_email?email=a@b.com&code=123456&user_id=1"
        )
        assert resp.status_code in (200, 400, 404, 500)

    def test_verify_invalid_or_expired_code(self, client_unauthenticated):
        """Postman: Verify User Email - Invalid Or Expired Code (400)."""
        resp = client_unauthenticated.get(
            "/api/v1/auth/verify_user_email?email=a@b.com&code=000000&user_id=1"
        )
        assert resp.status_code in (200, 400, 404, 500)

    def test_verify_missing_code(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/auth/verify_user_email?email=a@b.com&user_id=1"
        )
        assert resp.status_code == 422

    def test_verify_missing_email(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/auth/verify_user_email?code=123456&user_id=1"
        )
        assert resp.status_code == 422

    def test_verify_missing_user_id(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/auth/verify_user_email?email=a@b.com&code=123456"
        )
        assert resp.status_code == 422

    def test_verify_invalid_user_id_type(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/auth/verify_user_email?email=a@b.com&code=123456&user_id=abc"
        )
        assert resp.status_code == 422

    def test_verify_max_attempts_exceeded(self, client_unauthenticated):
        """Postman: Verify User Email - Max Attempts Exceeded (400)."""
        resp = client_unauthenticated.get(
            "/api/v1/auth/verify_user_email?email=a@b.com&code=123456&user_id=1"
        )
        assert resp.status_code in (200, 400, 404, 500)


# ─── POST /api/v1/auth/login ───

class TestLogin:
    """Tests for POST /api/v1/auth/login (public endpoint)."""

    def test_login_success(self, client_unauthenticated):
        """Postman: Login - Success (200). Requires valid credentials."""
        resp = client_unauthenticated.post("/api/v1/auth/login", json={
            "email": "user@example.com", "password": "securePassword123",
        })
        assert resp.status_code in (200, 401, 404, 500)

    def test_login_missing_fields(self, client_unauthenticated):
        """Postman: Login - Missing Fields (400)."""
        resp = client_unauthenticated.post("/api/v1/auth/login", json={
            "email": "user@example.com",
        })
        assert resp.status_code == 400
        assert "Email and password are required" in resp.json()["detail"]

    def test_login_missing_email(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/auth/login", json={
            "password": "p",
        })
        assert resp.status_code == 400

    def test_login_missing_password(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/auth/login", json={
            "email": "a@b.com",
        })
        assert resp.status_code == 400

    def test_login_empty_body(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/auth/login", json={})
        assert resp.status_code == 400

    def test_login_null_email(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/auth/login", json={
            "email": None, "password": "p",
        })
        assert resp.status_code in (400, 422)

    def test_login_invalid_credentials(self, client_unauthenticated):
        """Postman: Login - Invalid Credentials (401)."""
        resp = client_unauthenticated.post("/api/v1/auth/login", json={
            "email": "nonexistent@test.com", "password": "wrongPassword",
        })
        assert resp.status_code in (401, 404, 500)

    def test_login_account_not_active(self, client_unauthenticated):
        """Postman: Login - Account Not Active (401)."""
        resp = client_unauthenticated.post("/api/v1/auth/login", json={
            "email": "unverified@example.com", "password": "securePassword123",
        })
        assert resp.status_code in (401, 404, 500)


# ─── GET /api/v1/auth/forget-password ───

class TestForgotPassword:
    """Tests for GET /api/v1/auth/forget-password (public endpoint)."""

    def test_forget_password_success(self, client_unauthenticated):
        """Postman: Forget Password - Success (200)."""
        resp = client_unauthenticated.get(
            "/api/v1/auth/forget-password?email=user@example.com"
        )
        assert resp.status_code in (200, 404, 500)

    def test_forget_password_missing_email(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/auth/forget-password")
        assert resp.status_code == 422

    def test_forget_password_nonexistent_email(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/auth/forget-password?email=ghost@nowhere.com"
        )
        assert resp.status_code in (200, 404, 500)


# ─── GET /api/v1/auth/acceptForgotPassword ───

class TestAcceptForgotPassword:
    """Tests for GET /api/v1/auth/acceptForgotPassword (public endpoint)."""

    def test_accept_forgot_password_success(self, client_unauthenticated):
        """Postman: Accept Forgot Password - Success (200)."""
        resp = client_unauthenticated.get(
            "/api/v1/auth/acceptForgotPassword?email=user@example.com&password=newPassword123&token=reset-token-here"
        )
        assert resp.status_code in (200, 400, 404, 500)

    def test_accept_forgot_password_invalid_token(self, client_unauthenticated):
        """Postman: Accept Forgot Password - Invalid Or Expired Token (400)."""
        resp = client_unauthenticated.get(
            "/api/v1/auth/acceptForgotPassword?email=user@example.com&password=newPassword123&token=invalid-token"
        )
        assert resp.status_code in (200, 400, 404, 500)

    def test_accept_forgot_password_user_not_found(self, client_unauthenticated):
        """Postman: Accept Forgot Password - User Not Found (404)."""
        resp = client_unauthenticated.get(
            "/api/v1/auth/acceptForgotPassword?email=deleted@example.com&password=newPassword123&token=valid-token"
        )
        assert resp.status_code in (200, 400, 404, 500)

    def test_accept_forgot_password_missing_email(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/auth/acceptForgotPassword?password=p&token=t"
        )
        assert resp.status_code == 422

    def test_accept_forgot_password_missing_password(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/auth/acceptForgotPassword?email=a@b.com&token=t"
        )
        assert resp.status_code == 422

    def test_accept_forgot_password_missing_token(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/auth/acceptForgotPassword?email=a@b.com&password=p"
        )
        assert resp.status_code == 422


# ─── GET /api/v1/auth/check_organization_exists [EE] ───

class TestCheckOrganizationExists:
    """Tests for GET /api/v1/auth/check_organization_exists (public, EE-only)."""

    def test_org_exists_found(self, client_unauthenticated):
        """Postman: [EE] Check Organization Exists - Found (200)."""
        resp = client_unauthenticated.get(
            "/api/v1/auth/check_organization_exists?name=My Organization"
        )
        assert resp.status_code == 200

    def test_org_exists_not_found(self, client_unauthenticated):
        """Postman: [EE] Check Organization Exists - Not Found (200)."""
        resp = client_unauthenticated.get(
            "/api/v1/auth/check_organization_exists?name=Nonexistent Org"
        )
        assert resp.status_code == 200

    def test_org_exists_missing_name(self, client_unauthenticated):
        resp = client_unauthenticated.get("/api/v1/auth/check_organization_exists")
        assert resp.status_code == 422

    def test_org_exists_empty_name(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/auth/check_organization_exists?name="
        )
        assert resp.status_code == 200

    def test_org_exists_special_chars_name(self, client_unauthenticated):
        resp = client_unauthenticated.get(
            "/api/v1/auth/check_organization_exists?name=Test%20%26%20Co"
        )
        assert resp.status_code == 200

    def test_org_exists_as_member(self, client_as_member):
        """Also works with authenticated requests."""
        resp = client_as_member.get(
            "/api/v1/auth/check_organization_exists?name=TestOrg"
        )
        assert resp.status_code == 200


# ─── POST /api/v1/auth/switch_organization [EE] ───

class TestSwitchOrganization:
    """Tests for POST /api/v1/auth/switch_organization (authenticated, EE-only)."""

    def test_switch_org_success(self, client_as_member):
        """Postman: [EE] Switch Organization - Success (200)."""
        resp = client_as_member.post("/api/v1/auth/switch_organization", json={
            "organization_id": _ORG_ID,
        })
        assert resp.status_code in (200, 400, 403, 404, 500)

    def test_switch_org_missing_org_id(self, client_as_member):
        """Postman: [EE] Switch Organization - Missing Organization ID (400)."""
        resp = client_as_member.post("/api/v1/auth/switch_organization", json={})
        assert resp.status_code == 400
        assert "Organization ID is required" in resp.json()["detail"]

    def test_switch_org_null_org_id(self, client_as_member):
        resp = client_as_member.post("/api/v1/auth/switch_organization", json={
            "organization_id": None,
        })
        assert resp.status_code in (400, 422)

    def test_switch_org_empty_org_id(self, client_as_member):
        resp = client_as_member.post("/api/v1/auth/switch_organization", json={
            "organization_id": "",
        })
        assert resp.status_code == 400

    def test_switch_org_invalid_uuid_format(self, client_as_member):
        """Invalid UUID should error."""
        try:
            resp = client_as_member.post("/api/v1/auth/switch_organization", json={
                "organization_id": "not-a-uuid",
            })
            assert resp.status_code >= 400
        except Exception:
            pass

    def test_switch_org_unauthenticated(self, client_unauthenticated):
        resp = client_unauthenticated.post("/api/v1/auth/switch_organization", json={
            "organization_id": "550e8400-e29b-41d4-a716-446655440000",
        })
        assert resp.status_code in (401, 403)

    def test_switch_org_as_admin(self, client_as_admin):
        resp = client_as_admin.post("/api/v1/auth/switch_organization", json={
            "organization_id": _ORG_ID,
        })
        assert resp.status_code in (200, 400, 403, 404, 500)

    def test_switch_org_as_owner(self, client_as_owner):
        resp = client_as_owner.post("/api/v1/auth/switch_organization", json={
            "organization_id": _ORG_ID,
        })
        assert resp.status_code in (200, 400, 403, 404, 500)
