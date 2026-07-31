"""LLM-as-judge: scores one RAG answer against expected + retrieved context.

Returns ``{"verdict", "correctness", "groundedness", "relevance", "reasoning"}``.
Judge errors are captured (verdict=FAIL, reasoning=str(err)) so the run
continues instead of crashing halfway through."""

from __future__ import annotations

import json
import re
from typing import Iterable, Optional

import openai
from loguru import logger

from core.services.evals.prompt_loader import PromptLoader, render_prompt


class JudgeService:
    def __init__(
        self,
        *,
        prompt_loader: Optional[PromptLoader] = None,
        prompt_name: str = "judge_correctness.md",
    ):
        self._loader = prompt_loader or PromptLoader()
        self._prompt_name = prompt_name
        self._template: Optional[str] = None

    def _get_template(self) -> str:
        if self._template is None:
            self._template = self._loader.load(self._prompt_name)
        return self._template

    def judge(
        self,
        *,
        question: str,
        expected_answer: str,
        actual_answer: str,
        retrieved_chunks: Iterable[dict],
        api_key: str,
        model: str,
    ) -> dict:
        chunks_list = list(retrieved_chunks)
        logger.debug(
            "[eval] judge start model={} answer_chars={} chunks={}",
            model, len(actual_answer or ""), len(chunks_list),
        )
        prompt = render_prompt(
            self._get_template(),
            QUESTION=question,
            EXPECTED_ANSWER=expected_answer,
            ACTUAL_ANSWER=actual_answer,
            RETRIEVED_CONTEXT=_format_context(chunks_list),
        )
        try:
            client = openai.OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content or "{}"
            raw = _extract_json(content)
        except Exception as e:
            logger.exception("[eval] judge LLM call failed model={}", model)
            return {
                "verdict": "FAIL",
                "correctness": 0.0,
                "groundedness": 0.0,
                "relevance": 0.0,
                "reasoning": f"judge error: {type(e).__name__}: {e}",
            }

        verdict = str(raw.get("verdict", "FAIL")).upper()
        if verdict not in {"PASS", "PARTIAL", "FAIL"}:
            logger.debug(
                "[eval] judge returned unknown verdict={!r} model={}; coercing to FAIL",
                raw.get("verdict"), model,
            )
            verdict = "FAIL"

        return {
            "verdict": verdict,
            "correctness": _clamp01(raw.get("correctness")),
            "groundedness": _clamp01(raw.get("groundedness")),
            "relevance": _clamp01(raw.get("relevance")),
            "reasoning": str(raw.get("reasoning", ""))[:2000],
        }


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
        parts.append(f"[chunk {i}] {ch.get('text', '')}")
    return "\n\n".join(parts) if parts else "(no chunks retrieved)"


def _clamp01(v) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, f))
