"""Unit tests for per-assignment connection resolution in custom tools.

Pure logic — no DB or network (httpx and the connection resolver are stubbed).
Covers:
  - the pipeline cache round-trip preserving the stamped per-version override
    (``effective_oauth_connection_id``), and
  - the handler's header precedence: linked connection wins over inline
    ``auth_config`` for every auth type; inline is the fallback.

Run:
    pytest test-cases/test_connection_auth_resolution.py -v -o "addopts="
"""

import asyncio
from types import SimpleNamespace

import pytest

import core.services.custom_tool_service as cts
from core.services.custom_tool_service import (
    _CACHED_TOOL_FIELDS,
    create_custom_tool_handler,
    tool_from_cache,
)
from core.utils.oauth_resolution import effective_of, stamp_effective


class TestCacheRoundTrip:
    def test_effective_id_is_a_cached_field(self):
        assert "effective_oauth_connection_id" in _CACHED_TOOL_FIELDS

    def test_override_survives_cache_and_wins(self):
        tool = tool_from_cache(
            {
                "oauth_connection_id": "default-id",
                "effective_oauth_connection_id": "override-id",
            }
        )
        assert effective_of(tool) == "override-id"

    def test_no_override_falls_back_to_entity_default(self):
        tool = tool_from_cache(
            {"oauth_connection_id": "default-id", "effective_oauth_connection_id": None}
        )
        assert effective_of(tool) == "default-id"

    def test_stamp_then_serialize_shape(self):
        tool = SimpleNamespace(oauth_connection_id="default-id")
        stamp_effective(tool, "override-id")
        cached = {f: getattr(tool, f, None) for f in _CACHED_TOOL_FIELDS}
        assert cached["effective_oauth_connection_id"] == "override-id"
        assert effective_of(tool_from_cache(cached)) == "override-id"


class _StubResponse:
    status_code = 200
    text = "{}"

    def json(self):
        return {}


class _StubAsyncClient:
    """Captures the headers of the single request the handler makes."""

    captured: dict = {}

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, params=None, headers=None):
        _StubAsyncClient.captured = dict(headers or {})
        return _StubResponse()

    async def request(self, method, url, json=None, headers=None):
        _StubAsyncClient.captured = dict(headers or {})
        return _StubResponse()


def _run_handler(monkeypatch, tool, connection_header=None) -> dict:
    """Invoke the tool handler with stubs; return the request headers it sent.

    ``connection_header`` is the ``(name, value)`` pair the connection resolver
    would return (``None`` = no connection / resolution failed → fail-open)."""
    monkeypatch.setattr(cts.httpx, "AsyncClient", _StubAsyncClient)
    monkeypatch.setattr(
        cts, "_resolve_connection_header", lambda t: connection_header
    )
    _StubAsyncClient.captured = {}

    async def result_callback(_text):
        pass

    handler = create_custom_tool_handler(tool)
    params = SimpleNamespace(arguments={}, result_callback=result_callback)
    asyncio.get_event_loop().run_until_complete(handler(params))
    return _StubAsyncClient.captured


def _tool(auth_type, auth_config=None, connection_id=None):
    return SimpleNamespace(
        id=None,
        name="t",
        tool_type="custom",
        url="https://api.example.com/x",
        method="POST",
        auth_type=auth_type,
        auth_config=auth_config,
        oauth_connection_id=connection_id,
    )


class TestHandlerHeaderPrecedence:
    @pytest.mark.parametrize("auth_type", ["oauth", "bearer", "api_key"])
    def test_connection_wins_for_every_auth_type(self, monkeypatch, auth_type):
        tool = _tool(
            auth_type,
            auth_config={"token": "inline", "header": "X-API-Key", "value": "inline"},
            connection_id="conn-1",
        )
        headers = _run_handler(
            monkeypatch, tool, connection_header=("Authorization", "Bearer CONN_TOKEN")
        )
        assert headers["Authorization"] == "Bearer CONN_TOKEN"
        assert headers.get("X-API-Key") is None

    def test_api_key_connection_applies_custom_header(self, monkeypatch):
        # An API-key connection resolves to its custom header, not a bearer.
        tool = _tool(
            "bearer",
            auth_config={"token": "inline"},
            connection_id="conn-1",
        )
        headers = _run_handler(
            monkeypatch, tool, connection_header=("X-API-Key", "sk-live-123")
        )
        assert headers["X-API-Key"] == "sk-live-123"
        assert headers.get("Authorization") is None

    def test_inline_bearer_used_without_connection(self, monkeypatch):
        tool = _tool("bearer", auth_config={"token": "inline-tok"})
        headers = _run_handler(monkeypatch, tool)
        assert headers["Authorization"] == "Bearer inline-tok"

    def test_inline_api_key_used_without_connection(self, monkeypatch):
        tool = _tool("api_key", auth_config={"header": "X-Key", "value": "sk-1"})
        headers = _run_handler(monkeypatch, tool)
        assert headers["X-Key"] == "sk-1"

    def test_inline_fallback_when_connection_resolution_fails(self, monkeypatch):
        # Resolver returns None (logged failure) → fail-open to inline creds.
        tool = _tool("bearer", auth_config={"token": "inline-tok"}, connection_id="conn-1")
        headers = _run_handler(monkeypatch, tool, connection_header=None)
        assert headers["Authorization"] == "Bearer inline-tok"

    def test_oauth_without_connection_sends_no_auth_header(self, monkeypatch):
        tool = _tool("oauth")
        headers = _run_handler(monkeypatch, tool)
        assert "Authorization" not in headers


class TestResolveConnectionAuthHeader:
    """``OAuthService.resolve_connection_auth_header`` — the single place a
    connection is turned into an outgoing header, shared by the custom-tool and
    MCP runtimes. API-key connections produce a custom header; every other kind
    resolves to ``Authorization: Bearer``."""

    def _svc(self, monkeypatch, tokens=None, bearer=None):
        from core.services.oauth_service import OAuthService

        svc = OAuthService.__new__(OAuthService)
        monkeypatch.setattr(svc, "get_decrypted_tokens", lambda c: tokens or {}, raising=False)
        monkeypatch.setattr(
            svc, "get_valid_access_token_for_connection", lambda c: bearer, raising=False
        )
        return svc

    def _conn(self, auth_kind, auth_type, header_name=None):
        meta = {"auth_kind": auth_kind}
        if header_name is not None:
            meta["header_name"] = header_name
        return SimpleNamespace(
            public_metadata=meta, auth_type=auth_type, label="c", provider_slug="custom:c"
        )

    def test_api_key_uses_stored_header_name(self, monkeypatch):
        svc = self._svc(monkeypatch, tokens={"api_key": "sk-1"})
        conn = self._conn("api_key", "api_key", header_name="X-My-Key")
        assert svc.resolve_connection_auth_header(conn) == ("X-My-Key", "sk-1")

    def test_api_key_defaults_header_name(self, monkeypatch):
        svc = self._svc(monkeypatch, tokens={"api_key": "sk-1"})
        conn = self._conn("api_key", "api_key")
        assert svc.resolve_connection_auth_header(conn) == ("X-API-Key", "sk-1")

    def test_bearer_resolves_to_authorization(self, monkeypatch):
        svc = self._svc(monkeypatch, bearer="TOK")
        conn = self._conn("bearer", "bearer")
        assert svc.resolve_connection_auth_header(conn) == ("Authorization", "Bearer TOK")

    def test_api_key_without_stored_key_raises(self, monkeypatch):
        from fastapi import HTTPException

        svc = self._svc(monkeypatch, tokens={})
        conn = self._conn("api_key", "api_key")
        with pytest.raises(HTTPException):
            svc.resolve_connection_auth_header(conn)
