"""AI helpers for authoring agent system prompts.

A thin, non-pipeline wrapper around a single OpenAI chat completion used by the
prompt editor's **Generate** / **Improve** buttons. The API key is resolved per-org
(the org's stored OpenAI key) with a global ``settings.OPENAI_API_KEY`` fallback, so
this works in both multi-tenant and single-tenant setups.

Kept deliberately small — one prompt in, one block of prompt text out.
"""

from typing import Optional

from loguru import logger

from shared.config import settings

_GENERATE_MODEL = "gpt-4o"
# Generous cap so realistic voice-agent prompts aren't truncated; a `length` finish
# still raises rather than silently returning a cut-off prompt (see ``_complete``).
_MAX_OUTPUT_TOKENS = 4096


class PromptTruncatedError(Exception):
    """Raised when the model hit the output token cap and returned a cut-off prompt."""


_SYSTEM_INSTRUCTION = (
    "You are an expert prompt engineer for voice AI agents. You write clear, concise, "
    "instruction-style system prompts that steer a real-time phone agent. Prefer short "
    "sentences and bulleted Do/Don't guidance. Output ONLY the prompt text — no preamble, "
    "no markdown code fences, no commentary."
)


def resolve_openai_api_key(org_id) -> Optional[str]:
    """Org's OpenAI key (decrypted) if configured, else the global fallback."""
    try:
        from core.services.document_tool_service import get_openai_api_key_for_agent

        key = get_openai_api_key_for_agent(org_id)
        if key:
            return key
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("[ai] org OpenAI key lookup failed: {}", e)
    return settings.OPENAI_API_KEY or None


class AIGenerationService:
    """Generate or improve an agent system prompt with a single LLM call."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    # -- public API ---------------------------------------------------------- #
    def generate_system_prompt(
        self,
        agent_name: str = "",
        agent_description: str = "",
        agent_type: str = "",
        instruction: str = "",
    ) -> str:
        prompt = f"""Write a system prompt for a voice AI agent.

Agent name: {agent_name or "Untitled agent"}
Direction: {agent_type or "inbound"}
What the agent does: {agent_description or instruction or "a helpful, professional voice assistant"}

Cover, where relevant: the agent's role and goal, tone of voice, how to greet the
caller, the key tasks it should handle, and a few clear Do / Don't rules. Keep it tight
and instruction-style — it will be read aloud context for a live call."""
        return self._complete(prompt)

    def improve_system_prompt(
        self,
        text: str,
        agent_name: str = "",
        agent_description: str = "",
        agent_type: str = "",
    ) -> str:
        prompt = f"""Improve the following voice-agent system prompt. Make it clearer,
better structured, and more effective while preserving its intent and any existing
{{{{variable}}}} placeholders exactly as written.

Agent name: {agent_name or "Untitled agent"}
Direction: {agent_type or "inbound"}
Context: {agent_description or "n/a"}

Current prompt:
---
{text}
---

Return ONLY the improved prompt text."""
        return self._complete(prompt)

    # -- internal ------------------------------------------------------------ #
    def _complete(self, prompt: str) -> str:
        import openai

        client = openai.OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=_GENERATE_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_INSTRUCTION},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=_MAX_OUTPUT_TOKENS,
        )
        choice = response.choices[0]
        # A length finish means the model hit the token cap and the prompt is
        # truncated. The caller overwrites the user's existing prompt with this
        # text, so fail loudly rather than silently returning a cut-off prompt.
        if choice.finish_reason == "length":
            raise PromptTruncatedError(
                "The generated prompt was too long and got cut off. Please shorten "
                "the existing prompt or try again."
            )
        return (choice.message.content or "").strip()
