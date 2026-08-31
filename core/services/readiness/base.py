"""Base primitives for readiness checks.

Every check is a small class that subclasses ``ShallowCheck`` or ``DeepCheck``,
declares four class attributes (``id``, ``category``, ``severity``, ``depth`` —
depth is set by the marker parent), and implements ``run(ctx)`` returning a
``CheckResult``. The class-level constants make the registry legible and let the
runner filter without instantiating every check twice.

Cross-cutting concerns for live provider probes (timeouts, single retry on
transient errors) live here as decorators so individual Deep checks stay tiny
and consistent.
"""

from __future__ import annotations

import asyncio
import functools
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, ClassVar, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from core.services.readiness.schemas import (
    Category,
    CheckResult,
    Depth,
    ResourceRef,
    Severity,
    Status,
)


# ---------------------------------------------------------------------------
# Prefetched service triple (LLM / STT / TTS share this shape)
# ---------------------------------------------------------------------------


@dataclass
class ServiceSpec:
    """One resolved leg of the pipeline (LLM, STT, or TTS).

    Everything here is pre-fetched by the runner from a small number of batched
    queries so individual checks never re-query the DB. A field being ``None``
    is meaningful — it's what the check reports on.
    """

    # Raw JSONB settings from AgentConfig.{llm,stt,voice}_settings — kept so
    # provider-specific checks can read arbitrary keys without re-parsing.
    settings: Dict[str, Any] = field(default_factory=dict)
    # Ids extracted from settings (may be None when the user hasn't picked yet).
    provider_id: Optional[UUID] = None
    model_id: Optional[UUID] = None
    # Resolved rows (may be None when the id is set but the row is gone —
    # exactly the "orphan reference" state the integrity checks catch).
    provider: Optional[Any] = None  # ModelProvider
    model: Optional[Any] = None     # Model
    api_key: Optional[Any] = None   # ApiKey
    # Decrypted key value. ``None`` with ``api_key != None`` means the ciphertext
    # was there but decrypt raised — usually a JWT_SECRET_KEY rotation.
    decrypted_key: Optional[str] = None


# ---------------------------------------------------------------------------
# CheckContext — the "one bag" every check reads from
# ---------------------------------------------------------------------------


@dataclass
class CheckContext:
    """Everything a check needs, pre-fetched once by the runner.

    The runner builds this in a few batched queries; each check reads fields off
    it in memory. This is the DRY hub — no check touches the DB directly.
    """

    agent: Any                       # Agent row
    config: Optional[Any]            # AgentConfig row (may be None: brand-new agent)
    org_id: UUID
    db: Session                      # Session is here for the two checks that
    depth: Depth                     # legitimately need extra queries (workflow
                                     # graph validate, MCP live-probe delegate).

    # Config-derived
    is_s2s: bool = False

    # Prefetched service specs (LLM / STT / TTS). Always present — fields inside
    # may be None when the user hasn't configured that leg yet.
    llm: ServiceSpec = field(default_factory=ServiceSpec)
    stt: ServiceSpec = field(default_factory=ServiceSpec)
    tts: ServiceSpec = field(default_factory=ServiceSpec)

    # TTS voice — resolved from voice_settings.voice_id (may be a UUID or a raw
    # provider-native string; the row lookup succeeds only for the UUID case).
    voice: Optional[Any] = None      # ModelVoice row

    # Attachments (per this config version). Empty lists mean "nothing attached".
    phone_numbers: List[Any] = field(default_factory=list)
    tools: List[Any] = field(default_factory=list)
    knowledge_bases: List[Any] = field(default_factory=list)
    mcp_servers: List[Any] = field(default_factory=list)
    # Telephony channels linked to the agent (via AgentChannel). Independent
    # of ``phone_numbers`` — an outbound-only agent typically has a channel
    # but no assigned number, and the transport-credits deep check still
    # needs to probe that channel's account balance.
    channels: List[Any] = field(default_factory=list)


# ---------------------------------------------------------------------------
# BaseCheck — one class per rule
# ---------------------------------------------------------------------------


class BaseCheck(ABC):
    """Interface implemented by every readiness check.

    Class attributes describe the check; ``run`` performs it. Subclasses set
    ``id``, ``category``, ``severity``; ``depth`` is set by the marker parents
    (``ShallowCheck`` / ``DeepCheck``).
    """

    id: ClassVar[str]
    category: ClassVar[Category]
    severity: ClassVar[Severity]
    depth: ClassVar[Depth]

    def applies(self, ctx: CheckContext) -> bool:
        """Return False to declare this check inapplicable to the given context.

        The runner still records a ``SKIPPED`` result (with a reason) so the
        report is complete — the UI can show "STT: not required (S2S mode)"
        rather than pretending the check never existed.
        """
        return True

    def skip_reason(self, ctx: CheckContext) -> str:
        """Human-readable reason returned when ``applies`` is False. Override
        to give a specific explanation ("S2S mode handles STT internally")."""
        return "Not applicable to this configuration."

    @abstractmethod
    async def run(self, ctx: CheckContext) -> "CheckResult | List[CheckResult]":
        """Perform the check. Must always return a ``CheckResult`` — never raise
        for expected failure modes (empty config, revoked key, etc.). Use the
        ``_pass`` / ``_fail`` / ``_skip`` helpers below to build the result.

        A check MAY instead return a ``List[CheckResult]`` when one logical
        check reports on several independent resources and each deserves its
        own drawer row (e.g. one message per attached MCP server). The runner
        flattens the list; every entry must carry a unique ``check_id`` (use
        the ``check_id`` override on ``_pass`` / ``_fail``) so UIs can key on it.
        """

    # ── result constructors (keep individual checks DRY) ────────────────────

    def _result_id(self, suffix: str) -> str:
        """Per-resource ``check_id`` derived from this check's stable id, e.g.
        ``mcp_servers.reachable:<server-uuid>``. Lets a single check emit one
        row per resource while keeping ids unique + stable across runs (the
        prefix is the analytics key; the suffix scopes it to one resource)."""
        return f"{self.id}:{suffix}"

    def _pass(self, message: str, *, check_id: Optional[str] = None) -> CheckResult:
        """Build a PASS result. ``message`` is REQUIRED — a generic default
        would flood the drawer with meaningless "OK" rows. Say what the check
        actually verified so the UI can render each row informatively.

        ``check_id`` overrides the default (``self.id``) for per-resource rows."""
        return CheckResult(
            check_id=check_id or self.id,
            category=self.category,
            severity=self.severity,
            status=Status.PASS,
            message=message,
        )

    def _fail(
        self,
        message: str,
        *,
        remediation: Optional[str] = None,
        deep_link: Optional[str] = None,
        resource_ref: Optional[ResourceRef] = None,
        check_id: Optional[str] = None,
        severity: Optional[Severity] = None,
    ) -> CheckResult:
        """Build a FAIL result. ``severity`` overrides the check's class-level
        severity for the rare case where the *same* check wants a different
        weight for a specific failure mode — notably a timeout, which is
        "couldn't confirm" rather than "confirmed broken" and must not hard-block
        publish (see the timeout decorators below)."""
        return CheckResult(
            check_id=check_id or self.id,
            category=self.category,
            severity=severity or self.severity,
            status=Status.FAIL,
            message=message,
            remediation=remediation,
            deep_link=deep_link,
            resource_ref=resource_ref,
        )

    def _skip(self, reason: str) -> CheckResult:
        return CheckResult(
            check_id=self.id,
            category=self.category,
            severity=self.severity,
            status=Status.SKIPPED,
            message=reason,
            skip_reason=reason,
        )


class ShallowCheck(BaseCheck):
    """Marker parent for checks that only touch the DB / local memory."""

    depth: ClassVar[Depth] = Depth.SHALLOW


class DeepCheck(BaseCheck):
    """Marker parent for checks that make external network calls (providers,
    MCP servers, webhooks). These are the ones the safety-rail decorators
    below are designed for."""

    depth: ClassVar[Depth] = Depth.DEEP


# ---------------------------------------------------------------------------
# Cross-cutting decorators for Deep checks
# ---------------------------------------------------------------------------


class TransientProviderError(Exception):
    """Raised by Deep checks that hit 5xx/timeout and want retry semantics."""


def with_timeout(seconds: float, message: Optional[str] = None) -> Callable:
    """Bound a Deep check's ``run`` to ``seconds``. On timeout, returns a
    WARNING-style FAIL result instead of surfacing the exception — one slow
    provider must not break the entire report."""

    def deco(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(self: BaseCheck, ctx: CheckContext) -> CheckResult:
            try:
                return await asyncio.wait_for(fn(self, ctx), timeout=seconds)
            except asyncio.TimeoutError:
                # A timeout means "couldn't confirm in time", NOT "confirmed
                # broken" — a healthy-but-slow provider must not hard-block
                # publish. Always WARNING, regardless of the check's class
                # severity. Real failures (bad key, 4xx) come back as a
                # ProbeResult and keep the check's own (possibly BLOCKER) weight.
                return self._fail(
                    message
                    or f"Couldn't verify the provider within {seconds:g}s — it "
                    "may just be slow.",
                    remediation=(
                        "This is usually a temporary slowdown, not a broken "
                        "provider. Re-run the check in a moment."
                    ),
                    severity=Severity.WARNING,
                )

        return wrapper

    return deco


def with_retry(
    attempts: int = 2,
    on: Tuple[type, ...] = (TransientProviderError, asyncio.TimeoutError),
) -> Callable:
    """Retry a Deep check's ``run`` up to ``attempts`` times on transient errors.

    Configuration errors (4xx / invalid credentials) should NOT be raised as
    ``TransientProviderError`` — the caller wants those surfaced immediately as
    a FAIL result, not retried."""

    def deco(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(self: BaseCheck, ctx: CheckContext) -> CheckResult:
            last_exc: Optional[BaseException] = None
            for attempt in range(1, attempts + 1):
                try:
                    return await fn(self, ctx)
                except on as exc:
                    last_exc = exc
                    if attempt == attempts:
                        break
            # All attempts exhausted — return a FAIL result rather than raising.
            return self._fail(
                f"Provider probe failed after {attempts} attempts: {last_exc}",
                remediation=(
                    "The provider may be temporarily unavailable. "
                    "Re-run the readiness check in a minute."
                ),
            )

        return wrapper

    return deco


def with_timeout_and_retry(
    seconds: float,
    attempts: int = 2,
    message: Optional[str] = None,
) -> Callable:
    """Bound each attempt to ``seconds`` and retry up to ``attempts`` times on timeout.

    Stacking ``@with_retry`` over ``@with_timeout`` does NOT retry on timeouts —
    ``with_timeout`` catches ``asyncio.TimeoutError`` and returns a FAIL result,
    so ``with_retry``'s exception handler never sees it. This decorator gives
    EACH attempt its own fresh ``asyncio.wait_for`` budget and retries
    specifically on ``asyncio.TimeoutError``, closing that gap for the deep
    LLM/STT/TTS probes where a single transient network hiccup caused a
    healthy provider to be reported as a BLOCKER.

    Configuration errors (bad key, 4xx) already surface as ``ProbeResult(ok=
    False, ...)`` from the probes and are returned as-is by the wrapped ``run``
    — no exception, no retry, no false hope. Only bona-fide timeouts trigger a
    second attempt."""

    def deco(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(self: BaseCheck, ctx: CheckContext) -> CheckResult:
            for attempt in range(1, attempts + 1):
                try:
                    return await asyncio.wait_for(fn(self, ctx), timeout=seconds)
                except asyncio.TimeoutError:
                    if attempt == attempts:
                        # Timeout after every attempt = "couldn't confirm",
                        # not "confirmed broken". Downgrade to WARNING so a
                        # slow-but-healthy provider doesn't hard-block publish;
                        # a real bad-key/4xx failure returns a ProbeResult and
                        # keeps the check's BLOCKER weight. See ``with_timeout``.
                        return self._fail(
                            message
                            or (
                                f"Couldn't verify the provider within {seconds:g}s "
                                f"across {attempts} attempts — it may just be slow."
                            ),
                            remediation=(
                                "This is usually a temporary slowdown, not a "
                                "broken provider. Re-run the check in a moment."
                            ),
                            severity=Severity.WARNING,
                        )
            # unreachable — the loop either returns or falls through the
            # final-attempt branch above.
            raise RuntimeError("with_timeout_and_retry: exhausted loop without decision")

        return wrapper

    return deco
