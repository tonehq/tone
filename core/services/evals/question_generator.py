"""LLM-driven question generation for one document.

Takes extracted text + an OpenAI key, sends the ``question_generation.md``
prompt, and returns the parsed Q&A dict. Transport-agnostic — no DB, no
argparse; the caller (``EvalService.generate_eval``) persists the result."""

from __future__ import annotations

import json
import re
import time
from typing import Optional

import openai
from loguru import logger

from core.services.evals.errors import EvalGenerationError
from core.services.evals.prompt_loader import PromptLoader, render_prompt


class QuestionGeneratorService:
    def __init__(
        self,
        *,
        prompt_loader: Optional[PromptLoader] = None,
        prompt_name: str = "question_generation.md",
    ):
        self._loader = prompt_loader or PromptLoader()
        self._prompt_name = prompt_name

    def prompt_hash(self) -> str:
        return self._loader.hash(self._prompt_name)

    def generate(
        self,
        *,
        document_text: str,
        api_key: str,
        model: str,
        max_chars: int,
    ) -> dict:
        """Call the LLM; return ``{"generated_by_model": ..., "questions": [...]}``.

        Raises ``EvalGenerationError`` on network / parse / empty-response failures."""
        clipped = _clip_document(document_text, max_chars)
        template = self._loader.load(self._prompt_name)
        prompt = render_prompt(template, DOCUMENT_TEXT=clipped)

        logger.info(
            "[eval] question_gen calling model={} chars={} clipped={}",
            model, len(document_text), len(clipped),
        )
        t_start = time.monotonic()
        try:
            client = openai.OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            logger.exception("[eval] question generation LLM call failed model={}", model)
            raise EvalGenerationError(f"LLM call failed: {type(e).__name__}: {e}") from e

        content = resp.choices[0].message.content or "{}"
        try:
            parsed = _parse_response(content)
        except Exception as e:
            logger.exception("[eval] question generation returned unparseable JSON")
            raise EvalGenerationError(
                f"Unparseable question-generator output: {type(e).__name__}: {e}"
            ) from e

        questions = parsed.get("questions", [])
        if not isinstance(questions, list) or not questions:
            logger.error(
                "[eval] question generation returned empty/invalid questions array model={} raw_prefix={!r}",
                model, content[:200],
            )
            raise EvalGenerationError(
                "LLM did not return a non-empty `questions` array. "
                f"Raw response starts with: {content[:200]!r}"
            )

        for i, q in enumerate(questions, 1):
            q.setdefault("id", f"q{i}")
            q.setdefault("notes", "")
            q.setdefault("expected_source_snippet", "")

        logger.info(
            "[eval] question_gen ok model={} questions={} elapsed_s={:.1f}",
            model, len(questions), time.monotonic() - t_start,
        )
        return {"generated_by_model": model, "questions": questions}


def _clip_document(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return f"{text[:half]}\n\n…[TRUNCATED FOR PROMPT SIZE]…\n\n{text[-half:]}"


def _parse_response(raw: str) -> dict:
    stripped = raw.strip()
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
