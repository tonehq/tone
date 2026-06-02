"""Shared logging helpers."""

import json

# Tool args/outputs can be large; cap what we write to the logs.
LOG_VALUE_LIMIT = 2000


def truncate_for_log(value, limit: int = LOG_VALUE_LIMIT) -> str:
    """Render any tool argument/result as a single, length-capped log string."""
    try:
        text = value if isinstance(value, str) else json.dumps(value, default=str)
    except Exception:
        text = str(value)
    if len(text) > limit:
        return f"{text[:limit]}… [truncated {len(text) - limit} chars]"
    return text
