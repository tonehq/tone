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
    # First line only — validators sometimes append stack-ish context.
    text = text.splitlines()[0].strip()
    # Prefer the first sentence when the line is long and rambly (provider
    # errors often tack their own remediation on after the first sentence).
    if len(text) > 120 and ". " in text:
        text = text.split(". ", 1)[0]
    text = text.strip().rstrip(".").strip()
    if not text:
        return fallback
    if len(text) > 160:
        # Cut at a word boundary so we never chop a word mid-way ("publish
        # the…"), then drop a trailing separator before the ellipsis.
        text = (text[:160].rsplit(" ", 1)[0].rstrip() or text[:160]).rstrip(",;:—- ") + "…"
    if text[:2].isupper():
        return text
    return text[0].lower() + text[1:]


def oauth_failure_reason(detail: Any) -> str:
    """Map a raw OAuth/connection error into a clean, action-oriented clause.

    Provider token errors (``invalid_grant``, missing scopes, rejected client)
    are verbose and jargon-y; users only need to know *what to do*. Known cases
    map to a short "…— reconnect the account" clause; anything unrecognised
    falls back to :func:`humanize_reason` so we never lose signal.
    """
    text = str(detail or "").lower()
    if not text:
        return "its login couldn't be verified, reconnect the account"
    if "invalid_grant" in text or "expired or revoked" in text or (
        "token" in text and "expired" in text
    ):
        return "its login has expired, reconnect the account"
    if "scope" in text and ("insufficient" in text or "missing" in text or "denied" in text):
        return "it's missing required permissions, reconnect the account"
    if "invalid_client" in text or "unauthorized" in text or "access_denied" in text:
        return "its access was denied, reconnect the account"
    return humanize_reason(detail)
