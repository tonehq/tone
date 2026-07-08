"""Optional LLM analysis layer: summary, outcome, quality score, action items."""

import json
import os
from typing import Dict, Optional

from loguru import logger

from core.services.call_analysis.errors import AnalysisError, MissingKeyError
from core.services.call_analysis.schemas import LLMSection, MetricsSection
from core.services.call_analysis.stt_engine import STTResult

_DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-6",
}

# Keep head + tail of very long calls within a safe prompt size.
_MAX_TRANSCRIPT_CHARS = 60_000

_SYSTEM_PROMPT = (
    "You are a call-quality analyst for AI voice agents. You are given the "
    "diarized transcript of a finished call between an AI agent and a customer, "
    "plus computed call metrics. Respond ONLY with a JSON object with exactly "
    "these keys:\n"
    '  "summary": string (3-5 sentence summary of the call),\n'
    '  "call_outcome": string (short disposition label, e.g. "resolved", '
    '"escalated", "voicemail", "callback scheduled", "unresolved"),\n'
    '  "sentiment_arc": string (how caller sentiment evolved),\n'
    '  "agent_quality_score": integer 1-10,\n'
    '  "agent_quality_rationale": string,\n'
    '  "action_items": array of strings,\n'
    '  "compliance_flags": array of strings (empty if none).'
)


async def run_llm_analysis(
    stt: STTResult,
    metrics: Optional[MetricsSection],
    role_map: Optional[Dict[int, str]] = None,
    provider: str = "auto",
    model: Optional[str] = None,
) -> LLMSection:
    provider, api_key = _resolve_provider(provider)
    model = model or _DEFAULT_MODELS[provider]
    prompt = _build_prompt(stt, metrics, role_map or {})

    raw = await _complete(provider, api_key, model, prompt)
    try:
        section = _parse(raw)
    except Exception:
        logger.warning("LLM analysis JSON parse failed — retrying once")
        raw = await _complete(
            provider,
            api_key,
            model,
            prompt + "\n\nYour previous reply was not valid JSON. Return ONLY the JSON object.",
        )
        try:
            section = _parse(raw)
        except Exception as e:
            raise AnalysisError(f"LLM analysis returned unparseable output: {e}") from e

    section.provider = provider
    section.model = model
    return section


def _resolve_provider(provider: str) -> tuple:
    from dotenv import load_dotenv

    load_dotenv()
    candidates = (
        [("openai", "OPENAI_API_KEY"), ("anthropic", "ANTHROPIC_API_KEY")]
        if provider == "auto"
        else [(provider, f"{provider.upper()}_API_KEY")]
    )
    for name, env in candidates:
        key = os.getenv(env)
        if key:
            return name, key
    raise MissingKeyError(
        "No LLM API key configured (set OPENAI_API_KEY or ANTHROPIC_API_KEY)."
    )


def _build_prompt(stt: STTResult, metrics: Optional[MetricsSection], role_map: Dict[int, str]) -> str:
    lines = []
    for u in stt.utterances:
        role = role_map.get(u.speaker, f"speaker{u.speaker}") if u.speaker is not None else "speaker"
        lines.append(f"[{u.start:.1f}s] {role}: {u.text}")
    transcript = "\n".join(lines)
    truncated = ""
    if len(transcript) > _MAX_TRANSCRIPT_CHARS:
        half = _MAX_TRANSCRIPT_CHARS // 2
        transcript = (
            transcript[:half] + "\n... [transcript truncated] ...\n" + transcript[-half:]
        )
        truncated = "\nNote: the transcript was truncated in the middle due to length."

    metrics_summary = ""
    if metrics:
        metrics_summary = (
            f"\n\nCall metrics: duration {metrics.total_duration_seconds}s, "
            f"{metrics.turn_count} turns, silence {metrics.silence_pct}%, "
            f"{metrics.interruption_count} interruptions. "
            + " ".join(
                f"{s.role or 's' + str(s.speaker)}: {s.talk_time_pct}% talk time, "
                f"{s.wpm} wpm, {s.filler_word_count} fillers."
                for s in metrics.speakers
            )
        )

    extras = ""
    if stt.topics:
        extras += f"\nDetected topics: {', '.join(stt.topics)}"
    if stt.intents:
        extras += f"\nDetected intents: {', '.join(stt.intents)}"

    return f"Transcript:\n{transcript}{truncated}{metrics_summary}{extras}"


async def _complete(provider: str, api_key: str, model: str, prompt: str) -> str:
    if provider == "openai":
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        return response.choices[0].message.content or ""

    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=api_key)
    response = await client.messages.create(
        model=model,
        max_tokens=2000,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def _parse(raw: str) -> LLMSection:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in response")
    data = json.loads(text[start : end + 1])
    return LLMSection.model_validate(data)
