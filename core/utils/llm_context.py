"""Helpers for reading pipecat LLM context messages."""

from typing import Any


def flatten_message_content(content: Any) -> str:
    """Flatten an LLM message ``content`` to plain text.

    ``content`` is either a plain string or a list of content parts; for a list,
    the text of ``{"type": "text", "text": ...}`` parts is joined (non-text parts
    are ignored). Returns ``""`` for ``None`` or any unsupported shape.
    """
    if isinstance(content, list):
        return " ".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        )
    if isinstance(content, str):
        return content
    return ""
