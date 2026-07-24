"""Fuzzy retrieval-hit check.

Separates retrieval-side failures from synthesis-side failures: even if the
LLM's answer looks right, ``retrieval_hit=False`` means the expected passage
never made it to the context window."""

from __future__ import annotations

import re
from typing import List

_WORD_RE = re.compile(r"[a-z0-9]+")


def _normalize(text: str) -> List[str]:
    return _WORD_RE.findall(text.lower())


def retrieval_hit(expected_snippet: str, retrieved_texts: List[str]) -> bool:
    """Is a meaningful chunk of ``expected_snippet`` inside any retrieved text?

    Order-preserving greedy match — passes if ≥70% of the expected tokens appear
    in order inside any single retrieved chunk. Empty snippets (negative /
    out-of-scope questions) always pass."""
    if not expected_snippet or not expected_snippet.strip():
        return True

    exp = _normalize(expected_snippet)
    if not exp:
        return True

    if len(exp) < 4:
        joined = " ".join(_normalize(" ".join(retrieved_texts)))
        return " ".join(exp) in joined

    for text in retrieved_texts:
        toks = _normalize(text)
        if not toks:
            continue
        j = 0
        matched = 0
        for tok in toks:
            if j < len(exp) and tok == exp[j]:
                j += 1
                matched += 1
        if matched / len(exp) >= 0.7:
            return True
    return False
