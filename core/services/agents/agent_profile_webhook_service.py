"""``AgentProfileWebhookService`` — per-agent HTTP webhook data source for
profile variables (the generic replacement for the removed CRM lookup).

Two clearly separated parts (mirrors the old CRM design):
- **sync (DB)** — ``load_webhook_plan`` reads the config row + the empty,
  webhook-sourced variables into a frozen ``WebhookPlan``. Runs in the runner's
  executor, off the event loop.
- **async (network)** — ``enrich`` calls the user endpoint via ``httpx``, parses
  the JSON, and maps each variable's ``source_path`` onto
  ``{"profile.<key>": value}``. Takes the pre-loaded plan → opens NO session.

Every runtime failure degrades to ``{}`` (a slow/broken endpoint never fails an
inbound call — the variable falls back to its default ``value``). Phone numbers
and header values are NEVER logged.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import quote
from uuid import UUID

import httpx
from loguru import logger
from pydantic import TypeAdapter
from sqlalchemy.exc import IntegrityError

from core.models.agent_profile_variable import AgentProfileVariable
from core.models.agent_profile_webhook import AgentProfileWebhook
from core.services.agents.agent_profile_variable_service import PROFILE_PREFIX
from core.services.agents.errors import (
    ProfileWebhookInvalidError,
    ProfileWebhookNotFoundError,
)
from core.services.agents.profile_webhook_schemas import (
    RequestIdentifierIn,
    is_usable_scalar,
)
from core.services.base import BaseService
from core.services.custom_tool_service import _assert_safe_url
from core.utils.encryption import decrypt_json, encrypt_json


DEFAULT_TIMEOUT_SECONDS = 3
MIN_TIMEOUT_SECONDS = 1
MAX_TIMEOUT_SECONDS = 30
MAX_URL_LEN = 500
MAX_RESPONSE_CHARS = 8000
SUPPORTED_METHODS = frozenset({"GET", "POST"})

_IDENTIFIERS_ADAPTER: TypeAdapter = TypeAdapter(list[RequestIdentifierIn])

# Sentinel distinguishing "path segment absent" from a legit ``None`` value.
_MISSING = object()


# ── Response dot-path resolvers (recovered from the deleted CRM service) ─────


def _first_record(record: Any) -> Any:
    """A list response → its first item (locked with the user). A dict is
    returned as-is; anything else passes through."""
    if isinstance(record, list):
        return record[0] if record else None
    return record


def _descend(data: Any, path: str) -> Any:
    """Walk a dot-path, taking the first element whenever a segment lands on a
    list. Returns the node at ``path``, or ``_MISSING`` if any segment is
    absent."""
    cur: Any = data
    for seg in path.split("."):
        if isinstance(cur, list):
            cur = cur[0] if cur else None
        if not isinstance(cur, dict) or seg not in cur:
            return _MISSING
        cur = cur[seg]
    return cur


def _resolve_scalar(data: Any, path: str) -> Optional[str]:
    """Resolve a dot-path to a scalar string, or ``None`` when the path is
    missing or lands on a non-scalar (dict/list/None). Pydantic-backed scalar
    check (``is_usable_scalar``) so a mapping never injects ``"{...}"`` into the
    prompt — an unresolved mapping falls back to its default/blank."""
    node = _descend(data, path)
    if node is _MISSING:
        return None
    node = _first_record(node)
    if not is_usable_scalar(node):
        return None
    return str(node)


def _direction_enabled(directions: Optional[dict], direction: Optional[str]) -> bool:
    key = "outbound" if direction == "outbound" else "inbound"
    return bool((directions or {}).get(key))


@dataclass(frozen=True)
class WebhookPlan:
    """Resolved, per-call webhook enrichment plan (built by ``load_webhook_plan``)."""

    enabled: bool = False
    endpoint_url: Optional[str] = None
    http_method: str = "POST"
    headers_blob: Optional[dict] = None
    request_identifiers: list[dict] = field(default_factory=list)
    directions: dict = field(default_factory=dict)
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    # [(profile_key, source_path), ...] — only EMPTY, webhook-sourced variables.
    fill_plan: list[tuple[str, str]] = field(default_factory=list)

    @property
    def is_actionable(self) -> bool:
        return bool(self.enabled and self.endpoint_url and self.fill_plan)


@dataclass
class EnrichOutcome:
    """Result of a call-start enrichment: the ``{"profile.<key>": value}`` map to
    merge into the prompt, plus a ``tool_executions``-shaped record (``tool_type
    = "webhook"``) persisted for call debugging."""

    values: dict[str, str]
    execution: dict


class AgentProfileWebhookService(BaseService):
    """CRUD + runtime enrichment for one agent's webhook data source."""

    # ── Reads ────────────────────────────────────────────────────────────

    def get_webhook(self, agent_id: UUID) -> Optional[AgentProfileWebhook]:
        return (
            self.query(AgentProfileWebhook)
            .filter(AgentProfileWebhook.agent_id == agent_id)
            .first()
        )

    def webhook_response(self, row: AgentProfileWebhook) -> dict:
        """Owner-editing view: the secret-safe ``to_dict`` PLUS decrypted header
        values so the config form can round-trip them on save (full-replace).
        Returned only to an authed org member for their own agent."""
        data = row.to_dict()
        data["headers"] = self._decrypt_headers(row.headers)
        return data

    # ── Writes ───────────────────────────────────────────────────────────

    def upsert_webhook(
        self,
        agent_id: UUID,
        *,
        endpoint_url: str,
        http_method: str = "POST",
        headers: Optional[dict] = None,
        request_identifiers: Optional[list[dict]] = None,
        directions: Optional[dict] = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        is_enabled: bool = True,
    ) -> AgentProfileWebhook:
        url = (endpoint_url or "").strip()
        if not url or len(url) > MAX_URL_LEN:
            raise ProfileWebhookInvalidError(
                f"Endpoint URL is required and must be at most {MAX_URL_LEN} characters."
            )
        try:
            _assert_safe_url(url)
        except ValueError as exc:
            raise ProfileWebhookInvalidError(f"Invalid endpoint URL: {exc}") from exc

        method = (http_method or "POST").upper()
        if method not in SUPPORTED_METHODS:
            raise ProfileWebhookInvalidError(
                f"Unsupported HTTP method '{http_method}'. Use GET or POST."
            )

        identifiers = self._normalize_identifiers(request_identifiers)
        for ident in identifiers:
            if ident["in"] == "path" and ("{" + ident["param"] + "}") not in url:
                raise ProfileWebhookInvalidError(
                    f"Add the placeholder {{{ident['param']}}} to the Endpoint URL "
                    f"for the path identifier '{ident['param']}'."
                )
        dirs = self._normalize_directions(directions)
        timeout = max(MIN_TIMEOUT_SECONDS, min(MAX_TIMEOUT_SECONDS, int(timeout_seconds or DEFAULT_TIMEOUT_SECONDS)))
        headers_blob = encrypt_json(headers or {})

        row = self.get_webhook(agent_id)
        if row is None:
            row = AgentProfileWebhook(
                organization_id=self.org_id,
                agent_id=agent_id,
                endpoint_url=url,
                http_method=method,
                headers=headers_blob,
                request_identifiers=identifiers,
                directions=dirs,
                timeout_seconds=timeout,
                is_enabled=bool(is_enabled),
            )
            self.db.add(row)
        else:
            row.endpoint_url = url
            row.http_method = method
            row.headers = headers_blob  # full-replace (locked with user)
            row.request_identifiers = identifiers
            row.directions = dirs
            row.timeout_seconds = timeout
            row.is_enabled = bool(is_enabled)

        try:
            self.db.commit()
        except IntegrityError as exc:
            # Race with a concurrent insert — UNIQUE(agent_id) saves us.
            self.db.rollback()
            raise ProfileWebhookInvalidError(
                "A webhook is already configured for this agent."
            ) from exc
        self.db.refresh(row)
        return row

    def delete_webhook(self, agent_id: UUID) -> None:
        row = self.get_webhook(agent_id)
        if row is None:
            raise ProfileWebhookNotFoundError("No webhook configured for this agent.")
        self.db.delete(row)
        self.db.commit()

    # ── Runtime: sync plan load (executor) ────────────────────────────────

    def load_webhook_plan(self, agent_id: UUID) -> WebhookPlan:
        """Build the per-call plan: the config row + the EMPTY, webhook-sourced
        variables to fill. Runs in the runner's executor (off the loop)."""
        row = self.get_webhook(agent_id)
        if row is None or not row.is_enabled:
            return WebhookPlan(enabled=False)

        vars_ = (
            self.query(AgentProfileVariable)
            .filter(
                AgentProfileVariable.agent_id == agent_id,
                AgentProfileVariable.source == "webhook",
                AgentProfileVariable.source_path.isnot(None),
            )
            .all()
        )
        # Only fill variables whose static default is empty — never overwrite a
        # configured value (the fill-only-empty rule is also enforced at merge).
        fill_plan = [
            (v.key, v.source_path)
            for v in vars_
            if v.source_path and not (v.value or "").strip()
        ]
        return WebhookPlan(
            enabled=True,
            endpoint_url=row.endpoint_url,
            http_method=row.http_method or "POST",
            headers_blob=row.headers,
            request_identifiers=row.request_identifiers or [],
            directions=row.directions or {},
            timeout_seconds=row.timeout_seconds or DEFAULT_TIMEOUT_SECONDS,
            fill_plan=fill_plan,
        )

    # ── Runtime: async enrichment (network; no DB session) ────────────────

    async def enrich(
        self,
        *,
        plan: WebhookPlan,
        caller_phone: Optional[str],
        direction: Optional[str],
    ) -> EnrichOutcome:
        """Call the endpoint and return the filled ``{"profile.<key>": value}``
        map plus a ``webhook`` tool-execution record for call debugging. Any
        failure → empty values (the call continues; inbound variables fall back
        to their defaults); the record captures the status/response/error."""
        execution = self._base_execution(plan, caller_phone)
        if (
            not plan.is_actionable
            or not _direction_enabled(plan.directions, direction)
            or not (caller_phone or "").strip()
        ):
            execution["status"] = "cancelled"
            execution["result"] = "skipped (not applicable for this call)"
            return EnrichOutcome({}, execution)

        started = time.monotonic()
        try:
            status, parsed = await self._call_endpoint(
                endpoint_url=plan.endpoint_url,
                http_method=plan.http_method,
                headers_blob=plan.headers_blob,
                request_identifiers=plan.request_identifiers,
                caller_phone=caller_phone,
                timeout_seconds=plan.timeout_seconds,
            )
        except Exception:  # noqa: BLE001 — enrichment must never break a call
            logger.exception(
                "[profile-webhook] enrich request failed org={} direction={}",
                self.org_id,
                direction,
            )
            execution.update(
                status="error",
                result="error: request failed",
                error="request failed",
                duration_ms=int((time.monotonic() - started) * 1000),
            )
            return EnrichOutcome({}, execution)

        execution["duration_ms"] = int((time.monotonic() - started) * 1000)
        execution["status_code"] = status
        execution["result"] = parsed

        if not (200 <= status < 300):
            logger.warning(
                "[profile-webhook] non-2xx response org={} status={}",
                self.org_id,
                status,
            )
            execution.update(status="error", error=f"HTTP {status}")
            return EnrichOutcome({}, execution)

        record = _first_record(parsed)
        if not isinstance(record, dict):
            execution.update(status="error", error="response has no usable record")
            return EnrichOutcome({}, execution)

        filled: dict[str, str] = {}
        for key, source_path in plan.fill_plan:
            value = _resolve_scalar(record, source_path)
            if value is not None:
                filled[f"{PROFILE_PREFIX}{key}"] = value
        execution["status"] = "success"
        return EnrichOutcome(filled, execution)

    def _base_execution(self, plan: WebhookPlan, caller_phone: Optional[str]) -> dict:
        """A ``tool_executions``-shaped entry skeleton for this webhook call
        (``tool_type = "webhook"``). ``arguments`` is the request summary; the
        caller fills status/result/status_code/duration_ms. Same list the tool
        handlers use — persisted by ``record_executions`` at call end."""
        return {
            "tool": "Profile Webhook",
            "tool_type": "webhook",
            "arguments": {
                "method": plan.http_method,
                "url": plan.endpoint_url,
                "phone": caller_phone or "",
            },
            "turn": 0,
            "timestamp": int(time.time()),
        }

    def timeout_execution(self, plan: WebhookPlan, caller_phone: Optional[str]) -> dict:
        """The execution record for the timeout path (the task is cancelled by
        the runner's ``asyncio.wait_for``, so ``enrich`` never returns one)."""
        execution = self._base_execution(plan, caller_phone)
        secs = plan.timeout_seconds or DEFAULT_TIMEOUT_SECONDS
        execution.update(
            status="error",
            error=f"timed out after {secs}s",
            result=f"error: timed out after {secs}s",
            duration_ms=int(secs * 1000),
        )
        return execution

    # ── Test (config-time) ────────────────────────────────────────────────

    async def test_webhook(self, agent_id: UUID, sample_phone: str) -> dict:
        """Call the SAVED config with ``sample_phone`` and report the raw
        response + per-configured-path resolution. The only place a raw body is
        surfaced — authed + owner-scoped."""
        row = self.get_webhook(agent_id)
        if row is None:
            raise ProfileWebhookNotFoundError("No webhook configured for this agent.")

        paths = [
            v.source_path
            for v in self.query(AgentProfileVariable)
            .filter(
                AgentProfileVariable.agent_id == agent_id,
                AgentProfileVariable.source == "webhook",
                AgentProfileVariable.source_path.isnot(None),
            )
            .all()
            if v.source_path
        ]

        try:
            status, parsed = await self._call_endpoint(
                endpoint_url=row.endpoint_url,
                http_method=row.http_method or "POST",
                headers_blob=row.headers,
                request_identifiers=row.request_identifiers or [],
                caller_phone=sample_phone,
                timeout_seconds=row.timeout_seconds or DEFAULT_TIMEOUT_SECONDS,
            )
        except Exception:  # noqa: BLE001 — surface a clean failure, no secrets
            logger.exception("[profile-webhook] test request failed org={}", self.org_id)
            return {
                "ok": False,
                "status_code": None,
                "raw_response": None,
                "path_results": [{"path": p, "resolved": False, "value": None} for p in paths],
                "error": "Request failed — check the URL, method, and headers.",
            }

        record = _first_record(parsed)
        path_results = []
        for p in paths:
            value = _resolve_scalar(record, p) if isinstance(record, dict) else None
            path_results.append({"path": p, "resolved": value is not None, "value": value})

        return {
            "ok": 200 <= status < 300,
            "status_code": status,
            "raw_response": self._bounded(parsed),
            "path_results": path_results,
        }

    # ── Internal helpers ─────────────────────────────────────────────────

    async def _call_endpoint(
        self,
        *,
        endpoint_url: str,
        http_method: str,
        headers_blob: Optional[dict],
        request_identifiers: list[dict],
        caller_phone: Optional[str],
        timeout_seconds: int,
    ) -> tuple[int, Any]:
        url = endpoint_url
        query_params: dict[str, str] = {}
        body: dict[str, str] = {}
        for ident in request_identifiers or []:
            if ident.get("identifier") != "phone":
                continue
            name = (ident.get("param") or "").strip()
            if not name:
                continue
            loc = ident.get("in")
            value = caller_phone or ""
            if loc == "path":
                # Substitute ``{param}`` in the URL (URL-encoded); nothing added
                # to the query string or body for a path identifier.
                url = url.replace("{" + name + "}", quote(value, safe=""))
            elif loc == "query":
                query_params[name] = value
            else:  # body
                body[name] = value

        # Defense-in-depth: validate the FINAL url (after path substitution),
        # re-checked even though it was validated on save.
        _assert_safe_url(url)

        headers = self._clean_headers(self._decrypt_headers(headers_blob))
        method = (http_method or "POST").upper()

        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds)) as client:
            if method == "GET":
                resp = await client.get(
                    url, params=query_params or None, headers=headers or None
                )
            else:
                resp = await client.post(
                    url,
                    params=query_params or None,
                    json=body or None,
                    headers=headers or None,
                )
        try:
            parsed = resp.json()
        except Exception:  # noqa: BLE001 — non-JSON body → treat as no data
            parsed = None
        return resp.status_code, parsed

    def _decrypt_headers(self, headers_blob: Optional[dict]) -> dict:
        try:
            return decrypt_json(headers_blob) or {}
        except Exception:  # noqa: BLE001 — rotated key / corrupt blob
            logger.exception("[profile-webhook] header decrypt failed org={}", self.org_id)
            return {}

    @staticmethod
    def _clean_headers(headers: dict) -> dict:
        # Strip CR/LF from values to prevent header injection (mirrors
        # custom_tool_service._interp).
        return {
            str(k): str(v).replace("\r", "").replace("\n", "")
            for k, v in (headers or {}).items()
            if k
        }

    @staticmethod
    def _normalize_identifiers(raw: Optional[list[dict]]) -> list[dict]:
        try:
            parsed = _IDENTIFIERS_ADAPTER.validate_python(raw or [])
        except Exception as exc:  # noqa: BLE001 — bad identifier shape
            raise ProfileWebhookInvalidError(
                "Invalid request identifiers. Each needs identifier='phone', a "
                "param name, and in='query' or 'body'."
            ) from exc
        return [
            {"identifier": i.identifier, "param": i.param, "in": i.in_} for i in parsed
        ]

    @staticmethod
    def _normalize_directions(raw: Optional[dict]) -> dict:
        raw = raw or {}
        return {
            "inbound": bool(raw.get("inbound", True)),
            "outbound": bool(raw.get("outbound", False)),
        }

    @staticmethod
    def _bounded(parsed: Any) -> Any:
        try:
            s = json.dumps(parsed, default=str)
        except Exception:  # noqa: BLE001 — unserializable → stringify
            s = str(parsed)
        if len(s) > MAX_RESPONSE_CHARS:
            return s[:MAX_RESPONSE_CHARS] + "…(truncated)"
        return parsed
