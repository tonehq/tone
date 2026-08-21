"""Shared helpers for RAG observability.

One-liner utilities used by every vector-search call site so log lines are
consistent and comparable across ``read_document``, eval retrieval, and any
future retriever. Never expose secrets — this module only summarizes.
"""

from __future__ import annotations

import hashlib
from typing import Iterable, Optional, Sequence


# Cap the query text at this many characters before logging so a runaway
# prompt / long user utterance can't blow up a log line. 200 is enough to
# read the intent without becoming noise.
_MAX_QUERY_TEXT_CHARS = 200


def summarize_vector(embedding: Optional[Sequence[float]]) -> str:
    """Compact log-friendly summary of an embedding: ``dims=D hash=abcd12``.

    We NEVER log the raw float list — even one 1536-D vector fills a screen
    and adds zero debug value. The hash is stable across processes for the
    same input, so two log lines with the same ``hash`` correlate two
    different retrievals against the SAME embedding (useful for spotting
    "why are these two calls returning different chunks for the same query"
    when the query text is the same).
    """
    if embedding is None:
        return "dims=0 hash=none"
    # Sequence-of-float includes lists, tuples, numpy arrays; iterate once.
    floats = list(embedding)
    dims = len(floats)
    if dims == 0:
        return "dims=0 hash=empty"
    payload = ",".join(f"{x:.6f}" for x in floats).encode("utf-8")
    digest = hashlib.blake2b(payload, digest_size=4).hexdigest()  # 8 hex chars
    return f"dims={dims} hash={digest}"


def truncate_query_text(query: Optional[str], *, limit: int = _MAX_QUERY_TEXT_CHARS) -> str:
    """Trim a query string to ``limit`` chars for logging, appending an
    ellipsis marker on truncation so operators can tell it was cut."""
    if not query:
        return ""
    q = query.strip().replace("\n", " ")
    if len(q) <= limit:
        return q
    return q[:limit] + "…"


def format_scores(scores: Iterable[float], *, precision: int = 4) -> str:
    """`[0.1421, 0.1789]` style. Kept as a helper so every caller prints
    scores the same way (same precision, same brackets)."""
    return "[" + ", ".join(f"{s:.{precision}f}" for s in scores) + "]"
