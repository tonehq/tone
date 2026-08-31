"""Shared copy helpers for readiness check messages — the house style.

Every readiness message a user reads in the drawer should speak in one voice:

* **Name the thing in quotes** — ``“Gmail”``, ``“+14155550100”`` — via
  :func:`quote`, so a message always points at a specific resource.
* **Say the problem in plain words** — "can't be reached", "has no API key" —
  never an exception class name (``ConnectError``), never internal jargon
  ("probe failed", "handshake").
* **One message per failing thing.** A check that inspects several resources
  emits one row per resource that's broken (see ``base.BaseCheck._result_id``
  and the list-returning ``run`` contract), not one joined "A; B; +3 more"
  string.

Keeping these two helpers in one module means the voice is defined once and
reused by every category (LLM / STT / TTS / phone / tools / MCP / KB), instead
of each check re-inventing its own phrasing.
"""

from __future__ import annotations

from typing import Any


# Curly quotes match the pair used across the drawer copy. Kept as constants so
# the style is trivial to change in one place.
_LQUOTE = "“"  # “
_RQUOTE = "”"  # ”


def quote(name: Any) -> str:
    """Wrap a resource's user-facing name in the drawer's quote style.

    Falls back to a neutral placeholder when the name is empty so a message
    never renders dangling quotes (``“”``)."""
    text = str(name).strip() if name is not None else ""
    if not text:
        text = "this item"
    return f"{_LQUOTE}{text}{_RQUOTE}"


def humanize_reason(
    detail: Any,
    *,
    fallback: str = "the connection couldn't be established",
) -> str:
    """Trim a raw validator / provider error into one short, user-facing clause.

    Underlying validators raise messages that are already reasonably worded but
    can be long, multi-line, or end with stack-ish context. Keep the first
    line, drop trailing punctuation, and lower-case a leading capital (unless
    it's an acronym like ``OAuth`` / ``TLS``) so the clause reads naturally
    after "… — {reason}.".
    """
    text = str(detail or "").strip()
    if not text:
        return fallback
    text = text.splitlines()[0].strip().rstrip(".").strip()
    if not text:
        return fallback
    if len(text) > 160:
        text = text[:157].rstrip() + "…"  # …
    if text[:2].isupper():
        return text
    return text[0].lower() + text[1:]
