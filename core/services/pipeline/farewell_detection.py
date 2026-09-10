"""Spoken-farewell detection — a model-independent end-of-call signal.

The LLM sometimes speaks a closing farewell ("Thank you for calling — have a
great day!") but forgets to fire the ``end_call`` tool, leaving the caller on
the line (prod logs show this on both the two-step-confirm and direct-request
paths, across turns). The bot saying goodbye means it has ALREADY decided to
close — so the runner treats a spoken farewell with no ``end_call`` as a signal
to end the call itself. Pure code on the transcript text, so it works the same
regardless of which LLM the agent uses.

Kept deliberately tight to avoid ending a live call: only a message whose
*closing* is a clear farewell matches — a farewell buried mid-sentence does not.
"""

from __future__ import annotations

import re

# Clear closing phrases. Matched only at the END of the assistant's message
# (after trailing punctuation is stripped), so "have a great day tomorrow, now…"
# or "make sure to take care of the booking" never trigger.
FAREWELL_PHRASES: tuple[str, ...] = (
    "goodbye",
    "good bye",
    "bye",
    "bye bye",
    "have a great day",
    "have a good day",
    "have a nice day",
    "have a wonderful day",
    "have a great rest of your day",
    "have a good rest of your day",
    "thank you for calling",
    "thanks for calling",
    "take care",
)

# Trailing punctuation / whitespace / closing emoji-ish chars to strip before the
# end-of-message match, so "have a great day!" and "goodbye." both compare clean.
_TRAILING = re.compile(r"[\s.!?…,:;\"'）)\-—–]+$")


def is_farewell(text: str) -> bool:
    """True when the assistant's message *ends* with a clear farewell phrase.

    Model-independent: a farewell means the bot chose to close the call, so the
    runner can end it even if ``end_call`` was never fired. Ending-anchored to
    keep a mid-sentence pleasantry from tripping it.
    """
    if not text:
        return False
    normalized = _TRAILING.sub("", text.strip().lower())
    if not normalized:
        return False
    return any(normalized.endswith(phrase) for phrase in FAREWELL_PHRASES)
