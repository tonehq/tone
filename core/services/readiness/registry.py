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
    agent,
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
        # ── Agent-level content (prompt or workflow) ─────────────────────
        # First in the list so a completely un-configured agent surfaces
        # this specific blocker before the LLM/STT/TTS chain complains
        # about missing providers/keys.
        agent.AgentPromptOrWorkflowPresentCheck(),
        # Workflow validity — only applies in workflow mode; reads the
        # ``is_valid`` flag the workflow layer already computed on save.
        agent.AgentWorkflowValidCheck(),
        # Outbound-only / both agents warn when there's nothing to dial.
        agent.AgentOutboundHasWorkCheck(),

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
        stt.STTLanguageConfiguredCheck(),
        # Model ↔ language consistency — SKIPs when the model has no
        # seeded ModelLanguage rows so legacy models don't regress.
        stt.STTModelLanguageMatchCheck(),

        # ── TTS (skipped if S2S) ──────────────────────────────────────────
        tts.TTSProviderConfiguredCheck(),
        tts.TTSModelConfiguredCheck(),
        tts.TTSApiKeyPresentCheck(),
        tts.TTSApiKeyDecryptsCheck(),
        tts.TTSLanguageConfiguredCheck(),
        # Model ↔ language consistency — SKIPs when metadata not seeded.
        tts.TTSModelLanguageMatchCheck(),
        tts.TTSVoiceSelectedCheck(),
        tts.TTSVoiceModelMatchCheck(),
        # Voice ↔ language consistency — SKIPs when the voice row has no
        # ``language_list`` metadata so legacy voices don't regress.
        tts.TTSVoiceLanguageMatchCheck(),

        # ── Phone & channel routing (severity depends on agent_type) ─────
        phone.PhoneAssignedIfInboundCheck(),
        phone.PhoneChannelReachableCheck(),

        # ── Attached resources (per-item WARNINGs; agent still runs) ─────
        tools.ToolsUsableCheck(),
        # OAuth-expiry shallow checks: pure-DB read of ``token_expiry`` from
        # the linked ``OAuthConnection``. Cheap enough for the agent-list
        # badge; complements the reachable-deep checks that would otherwise
        # be the only place expiry surfaces.
        tools.ToolOAuthTokenValidCheck(),
        # KB embedding checks first, then the per-KB structural chain — a
        # missing embedding model is the root cause of "no retrieval at all",
        # so surfacing that before per-KB details keeps the drawer readable.
        knowledge_bases.KnowledgeBaseEmbeddingModelConfiguredCheck(),
        knowledge_bases.KnowledgeBaseEmbeddingKeyUsableCheck(),
        # Vector-space consistency: agent's embedding model must match the
        # one used at ingestion time or retrieval returns garbage.
        knowledge_bases.KnowledgeBaseEmbeddingMatchCheck(),
        knowledge_bases.KnowledgeBasesReadyCheck(),
        mcp_servers.McpServersConfiguredCheck(),
        mcp_servers.McpServerOAuthTokenValidCheck(),

        # ── Deep checks (live provider / server probes) ──────────────────
        llm.LLMProviderReachableCheck(),
        stt.STTProviderReachableCheck(),
        tts.TTSProviderReachableCheck(),
        # Transport (Twilio / Telnyx / Plivo / Exotel): hits the provider
        # account/balance endpoint to catch revoked credentials + credit
        # exhaustion — the two failure modes the shallow phone check misses.
        phone.TransportCreditsReachableCheck(),
        # Per-number verification: exists at provider + voice-capable +
        # (Twilio/Telnyx) inbound webhook points to Tone. Sits after the
        # transport-credits check so a broken account attributes to the
        # right layer.
        phone.PhoneNumberVerifiedAtProviderCheck(),
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
