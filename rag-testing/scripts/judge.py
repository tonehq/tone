"""LLM-as-judge: scores a RAG answer against the expected answer + retrieved context.

Returns a dict shaped as:
    {
        "verdict": "PASS" | "PARTIAL" | "FAIL",
        "correctness": float,
        "groundedness": float,
        "relevance": float,
        "reasoning": str
    }
"""
from __future__ import annotations

import json
import re
from typing import Iterable, Optional

from common import openai_client, read_prompt, render_prompt

_JUDGE_MODEL_DEFAULT = "gpt-4o"

_TEMPLATE = None


def _template() -> str:
    global _TEMPLATE
    if _TEMPLATE is None:
        _TEMPLATE = read_prompt("judge_correctness.md")
    return _TEMPLATE


def _extract_json(text: str) -> dict:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _format_context(chunks: Iterable[dict]) -> str:
    parts = []
    for i, ch in enumerate(chunks, 1):
        text = ch.get("text", "")
        parts.append(f"[chunk {i}] {text}")
    return "\n\n".join(parts) if parts else "(no chunks retrieved)"


def judge_answer(
    *,
    question: str,
    expected_answer: str,
    actual_answer: str,
    retrieved_chunks: Iterable[dict],
    model: str = _JUDGE_MODEL_DEFAULT,
    client: Optional[object] = None,
) -> dict:
    """Score one RAG answer. Returns a normalized verdict dict.

    On judge error (LLM down, unparseable output), returns a FAIL verdict with
    the raw error captured in `reasoning` so the run continues.
    """
    client = client or openai_client()
    prompt = render_prompt(
        _template(),
        QUESTION=question,
        EXPECTED_ANSWER=expected_answer,
        ACTUAL_ANSWER=actual_answer,
        RETRIEVED_CONTEXT=_format_context(retrieved_chunks),
    )
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
        raw = _extract_json(content)
    except Exception as e:
        return {
            "verdict": "FAIL",
            "correctness": 0.0,
            "groundedness": 0.0,
            "relevance": 0.0,
            "reasoning": f"judge error: {type(e).__name__}: {e}",
        }

    verdict = str(raw.get("verdict", "FAIL")).upper()
    if verdict not in {"PASS", "PARTIAL", "FAIL"}:
        verdict = "FAIL"

    def _fclamp(v, default=0.0):
        try:
            f = float(v)
        except (TypeError, ValueError):
            return default
        return max(0.0, min(1.0, f))

    return {
        "verdict": verdict,
        "correctness": _fclamp(raw.get("correctness")),
        "groundedness": _fclamp(raw.get("groundedness")),
        "relevance": _fclamp(raw.get("relevance")),
        "reasoning": str(raw.get("reasoning", ""))[:2000],
    }
