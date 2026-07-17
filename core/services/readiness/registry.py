"""Registry of readiness checks.

Scoped to external services and attached resources only — the checks that
depend on things that CAN fail at runtime (provider credentials, live server
reachability, per-resource configuration). Internal-state checks (agent
existence, config presence, prompt filled, cross-org integrity, billing,
greeting) were removed: those are either always true in a healthy system or
enforced elsewhere in the CRUD layer.

Adding a rule is one import + one line in ``_REGISTRY``.
"""

from __future__ import annotations

from typing import List

from core.services.readiness.base import BaseCheck
from core.services.readiness.checks import (
    llm,
    mcp_servers,
    phone,
    stt,
    tools,
    tts,
    knowledge_bases,
)
from core.services.readiness.schemas import Depth


def _build_registry() -> List[BaseCheck]:
    return [
        # ── LLM ────────────────────────────────────────────────────────────
        llm.LLMProviderConfiguredCheck(),
        llm.LLMModelConfiguredCheck(),
        llm.LLMApiKeyPresentCheck(),
        llm.LLMApiKeyDecryptsCheck(),

        # ── STT (skipped if S2S) ──────────────────────────────────────────
        stt.STTProviderConfiguredCheck(),
        stt.STTModelConfiguredCheck(),
        stt.STTApiKeyPresentCheck(),
        stt.STTApiKeyDecryptsCheck(),

        # ── TTS (skipped if S2S) ──────────────────────────────────────────
        tts.TTSProviderConfiguredCheck(),
        tts.TTSModelConfiguredCheck(),
        tts.TTSApiKeyPresentCheck(),
        tts.TTSApiKeyDecryptsCheck(),
        tts.TTSVoiceSelectedCheck(),
        tts.TTSVoiceModelMatchCheck(),

        # ── Phone & channel routing (severity depends on agent_type) ─────
        phone.PhoneAssignedIfInboundCheck(),
        phone.PhoneChannelReachableCheck(),

        # ── Attached resources (per-item WARNINGs; agent still runs) ─────
        tools.ToolsUsableCheck(),
        knowledge_bases.KnowledgeBasesReadyCheck(),
        mcp_servers.McpServersConfiguredCheck(),

        # ── Deep checks (live provider / server probes) ──────────────────
        llm.LLMProviderReachableCheck(),
        stt.STTProviderReachableCheck(),
        tts.TTSProviderReachableCheck(),
        # Transport (Twilio / Telnyx / Plivo / Exotel): hits the provider
        # account/balance endpoint to catch revoked credentials + credit
        # exhaustion — the two failure modes the shallow phone check misses.
        phone.TransportCreditsReachableCheck(),
        # MCP: order matters — L4 HTTP probe first so an unreachable server
        # attributes to `http_reachable`, not to a confusing handshake failure.
        mcp_servers.McpServerHttpReachableCheck(),
        mcp_servers.McpServerReachableCheck(),
        # Tools: live GET probe. Non-GET tools are skipped inside the check.
        tools.ToolReachableCheck(),
    ]


_REGISTRY: List[BaseCheck] = _build_registry()


def get_checks(depth: Depth) -> List[BaseCheck]:
    """Return the checks that should run at the requested depth.

    Shallow → shallow checks only. Deep → everything (shallow + deep) so a
    Deep report is always a superset of a Shallow one; UIs can render either
    from the same data.
    """
    if depth == Depth.SHALLOW:
        return [c for c in _REGISTRY if c.depth == Depth.SHALLOW]
    return list(_REGISTRY)
