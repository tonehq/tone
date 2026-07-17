"""Unit tests for the httpOnly auth-cookie helpers.

Source: core/middleware/auth.py
Pure/fast — no DB, no TestClient. Exercises cookie set/clear/extraction and the
`set_cookies_and_strip` response shaper used by every token-issuing route.
"""

from fastapi import Response
from starlette.requests import Request

from shared.config import settings
from core.middleware.auth import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    REFRESH_COOKIE_PATH,
    clear_auth_cookies,
    get_bearer_or_cookie_token,
    set_auth_cookies,
    set_cookies_and_strip,
)


def _set_cookie_headers(response: Response):
    """All Set-Cookie header values on a response (one per cookie)."""
    return [v.decode() for (k, v) in response.raw_headers if k == b"set-cookie"]


def _cookie(headers, name):
    return next((h for h in headers if h.startswith(f"{name}=")), None)


def _make_request(headers: dict) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "headers": raw})


# ─── set_auth_cookies ───

class TestSetAuthCookies:
    def test_sets_both_cookies_httponly(self):
        resp = Response()
        set_auth_cookies(resp, "access-jwt", "refresh-jwt")
        headers = _set_cookie_headers(resp)

        access = _cookie(headers, ACCESS_COOKIE)
        refresh = _cookie(headers, REFRESH_COOKIE)
        assert access is not None and refresh is not None
        assert "access-jwt" in access and "refresh-jwt" in refresh
        # Both must be httpOnly so JS can never read them.
        assert "httponly" in access.lower()
        assert "httponly" in refresh.lower()

    def test_cookie_paths_and_session_max_age(self):
        resp = Response()
        set_auth_cookies(resp, "a", "r")
        headers = _set_cookie_headers(resp)
        access = _cookie(headers, ACCESS_COOKIE)
        refresh = _cookie(headers, REFRESH_COOKIE)

        # Both cookies are site-wide (Path=/) — REFRESH_COOKIE_PATH is "/".
        assert "Path=/" in access
        assert f"Path={REFRESH_COOKIE_PATH}" in refresh

        # Both carry the *session* (refresh-token) lifetime, not the short
        # access-token TTL — so the FE middleware presence-check survives a
        # silent refresh.
        session_max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
        assert f"Max-Age={session_max_age}" in access
        assert f"Max-Age={session_max_age}" in refresh

    def test_samesite_from_settings(self):
        resp = Response()
        set_auth_cookies(resp, "a", "r")
        access = _cookie(_set_cookie_headers(resp), ACCESS_COOKIE)
        assert f"samesite={settings.COOKIE_SAMESITE}".lower() in access.lower()

    def test_access_only_when_no_refresh(self):
        resp = Response()
        set_auth_cookies(resp, "access-jwt")  # refresh omitted
        headers = _set_cookie_headers(resp)
        assert _cookie(headers, ACCESS_COOKIE) is not None
        assert _cookie(headers, REFRESH_COOKIE) is None


# ─── clear_auth_cookies ───

class TestClearAuthCookies:
    def test_expires_both_cookies(self):
        resp = Response()
        clear_auth_cookies(resp)
        headers = _set_cookie_headers(resp)
        access = _cookie(headers, ACCESS_COOKIE)
        refresh = _cookie(headers, REFRESH_COOKIE)
        assert access is not None and refresh is not None
        # delete_cookie zeroes Max-Age so the browser drops them immediately.
        assert "Max-Age=0" in access
        assert "Max-Age=0" in refresh
        assert f"Path={REFRESH_COOKIE_PATH}" in refresh


# ─── get_bearer_or_cookie_token ───

class TestTokenExtraction:
    def test_prefers_authorization_header(self):
        req = _make_request(
            {"authorization": "Bearer header-tok", "cookie": f"{ACCESS_COOKIE}=cookie-tok"}
        )
        assert get_bearer_or_cookie_token(req) == "header-tok"

    def test_falls_back_to_cookie(self):
        req = _make_request({"cookie": f"{ACCESS_COOKIE}=cookie-tok"})
        assert get_bearer_or_cookie_token(req) == "cookie-tok"

    def test_none_when_neither_present(self):
        req = _make_request({})
        assert get_bearer_or_cookie_token(req) is None

    def test_ignores_non_bearer_scheme(self):
        # No cookie, non-Bearer header → nothing usable.
        req = _make_request({"authorization": "Basic abc123"})
        assert get_bearer_or_cookie_token(req) is None


# ─── set_cookies_and_strip ───

class TestSetCookiesAndStrip:
    def test_strips_tokens_and_sets_cookies(self):
        resp = Response()
        result = set_cookies_and_strip(
            resp,
            {
                "access_token": "a",
                "refresh_token": "r",
                "user": {"id": "u1"},
                "role": "owner",
            },
        )
        # Tokens moved to cookies, removed from the JSON body.
        assert "access_token" not in result
        assert "refresh_token" not in result
        assert result["user"] == {"id": "u1"}
        assert result["role"] == "owner"
        headers = _set_cookie_headers(resp)
        assert _cookie(headers, ACCESS_COOKIE) is not None
        assert _cookie(headers, REFRESH_COOKIE) is not None

    def test_noop_without_access_token(self):
        resp = Response()
        payload = {"message": "verify your email"}
        result = set_cookies_and_strip(resp, payload)
        assert result == payload
        assert _set_cookie_headers(resp) == []
