"""Runtime template variables for agent system prompts.

The frontend prompt editor inserts variables as ``{{key}}`` placeholders (see
``frontend/src/constants/promptVariables.ts`` — KEEP THE KEY SET IN SYNC). At call
time we replace each *known* ``{{key}}`` with a value derived from the live call;
unknown placeholders are left untouched so free-form text is never mangled.

Substitution is applied PER CALL (in the builder, via ``PipelineParams``), never in
the resolver's Redis-cached payload — that cache is shared across every call for an
agent, so baking a single call's caller number into it would leak across calls.
"""

import re
from datetime import datetime, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

# Canonical variable keys exposed to the prompt editor. Keep in sync with the
# frontend registry (frontend/src/constants/promptVariables.ts).
PROMPT_VARIABLE_KEYS = (
    "caller_number",
    "callee_number",
    "agent_name",
    "current_date",
    "current_time",
    "call_direction",
)

# Matches {{ key }} or {{ key|default }} (custom variables carry their default inline,
# after a pipe). Inner whitespace around the key is tolerated; the default runs up to `}`.
# The key is an identifier optionally followed by dotted identifier segments — so
# ``{{profile.customer_name}}`` matches but incidental prose like ``{{1.0|draft}}``
# does NOT (segments must start with a letter/underscore, no consecutive dots, no
# trailing dot). This is a strict superset of the pre-Profile ``[a-zA-Z_][a-zA-Z0-9_]*``
# behaviour — flat keys still match unchanged.
_TOKEN_RE = re.compile(
    r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s*(?:\|([^}]*))?\}\}"
)


def _now_in_agent_tz() -> datetime:
    """Current time in AGENT_TIMEZONE (default UTC), mirroring build_date_preamble."""
    from core.config import settings

    tz_name = getattr(settings, "AGENT_TIMEZONE", None) or "UTC"
    try:
        return datetime.now(ZoneInfo(tz_name))
    except Exception:
        return datetime.now(timezone.utc)


def build_call_context(
    agent: Any = None,
    call_data: Optional[dict] = None,
    transport_type: Optional[str] = None,
    profile_variables: Optional[dict] = None,
) -> dict:
    """Resolve a ``{key: value}`` map for every known variable from live call data.

    Values are best-effort: a missing field resolves to ``""`` so an unanswered
    ``{{caller_number}}`` is removed rather than left as literal braces in the prompt.
    ``transport_type`` is accepted for forward-compatibility (future variables) but is
    not required by any current key.

    ``profile_variables`` is the per-agent profile map already in
    ``{"profile.<key>": <value>}`` shape (produced by
    ``AgentProfileVariableService.get_variables_map``). It is merged into the
    returned dict; passing ``None`` preserves the pre-Profile-Variables behavior
    exactly.
    """
    call_data = call_data or {}
    now = _now_in_agent_tz()
    context = {
        "caller_number": call_data.get("from", "") or "",
        "callee_number": call_data.get("to", "") or "",
        "agent_name": getattr(agent, "name", "") or "",
        "current_date": now.strftime("%Y-%m-%d"),
        "current_time": now.strftime("%H:%M"),
        "call_direction": getattr(agent, "agent_type", "") or "",
    }
    if profile_variables:
        context.update(profile_variables)
    return context


def substitute_variables(text: Optional[str], context: Optional[dict]) -> Optional[str]:
    """Replace ``{{...}}`` tokens with their runtime value.

    Resolution order per token:
      1. ``{{key}}`` where ``key`` is a known system variable → the live value.
      2. ``{{key|default}}`` (custom variable) → its inline default value.
      3. anything else (unknown key, no default) → returned verbatim.

    ``context`` may be falsy (e.g. no call data); custom-variable defaults are still
    applied since they don't depend on it.
    """
    if not text:
        return text
    ctx = context or {}

    def _replace(match: "re.Match[str]") -> str:
        key = match.group(1)
        default = match.group(2)  # None when there is no `|default`
        if key in ctx:
            return str(ctx[key])
        if default is not None:
            return default
        return match.group(0)

    return _TOKEN_RE.sub(_replace, text)
