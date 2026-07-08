"""Batch (prerecorded) transcription via Deepgram — the primary analysis engine.

Uses the deepgram-sdk 7.x surface: AsyncDeepgramClient().listen.v1.media.transcribe_file(...).
"""

import asyncio
import os
from typing import Any, Dict, List, Optional

from loguru import logger
from pydantic import BaseModel

from core.services.call_analysis.errors import AnalysisError, MissingKeyError
from core.services.call_analysis.schemas import Utterance, Word

# Deepgram intelligence features are English-only; dropped (with a warning) if
# the request fails or the audio is non-English.
_INTELLIGENCE_KWARGS = {
    "sentiment": True,
    "topics": True,
    "intents": True,
    "summarize": "v2",
}

_REQUEST_TIMEOUT_SECONDS = 120


class STTResult(BaseModel):
    model: str
    duration: float
    language: Optional[str] = None
    words: List[Word] = []
    utterances: List[Utterance] = []
    topics: List[str] = []
    intents: List[str] = []
    summary: Optional[str] = None
    warnings: List[str] = []


def _resolve_api_key(api_key: Optional[str]) -> str:
    if not api_key:
        from dotenv import load_dotenv

        load_dotenv()
    key = api_key or os.getenv("DEEPGRAM_API_KEY")
    if not key:
        raise MissingKeyError(
            "DEEPGRAM_API_KEY is not set. STT is the primary analysis engine — "
            "export DEEPGRAM_API_KEY and retry."
        )
    return key


async def transcribe(
    audio_bytes: bytes,
    mime: str = "audio/mpeg",
    model: str = "nova-3",
    api_key: Optional[str] = None,
) -> STTResult:
    """Batch-transcribe audio with diarization, word timings and (when possible)
    sentiment/topics/intents/summary. Raises AnalysisError on failure."""
    from deepgram import AsyncDeepgramClient
    from deepgram.core.api_error import ApiError

    key = _resolve_api_key(api_key)
    client = AsyncDeepgramClient(api_key=key)
    warnings: List[str] = []

    base_kwargs: Dict[str, Any] = {
        "model": model,
        "smart_format": True,
        "punctuate": True,
        "diarize": True,
        "utterances": True,
        "filler_words": True,
    }
    request_options = {
        "timeout_in_seconds": _REQUEST_TIMEOUT_SECONDS,
        "additional_headers": {"Content-Type": mime},
    }

    async def _call(kwargs: Dict[str, Any]):
        return await client.listen.v1.media.transcribe_file(
            request=audio_bytes, request_options=request_options, **kwargs
        )

    attempts = [
        {**base_kwargs, **_INTELLIGENCE_KWARGS},
        base_kwargs,  # fallback: non-English audio rejects intelligence features
    ]
    response = None
    last_error: Optional[Exception] = None
    for i, kwargs in enumerate(attempts):
        try:
            response = await _call(kwargs)
            break
        except ApiError as e:
            last_error = e
            if e.status_code == 401:
                raise AnalysisError(
                    "Deepgram rejected the API key (401). Check DEEPGRAM_API_KEY."
                ) from e
            if e.status_code in (429, 500, 502, 503, 504):
                logger.warning("Deepgram {} — retrying once", e.status_code)
                await asyncio.sleep(2)
                try:
                    response = await _call(kwargs)
                    break
                except ApiError as e2:
                    last_error = e2
                    continue
            if e.status_code == 400 and i == 0:
                warnings.append(
                    "Deepgram intelligence features (sentiment/topics/intents/summary) "
                    "unavailable for this audio — likely non-English; continued without them."
                )
                continue
            raise AnalysisError(f"Deepgram transcription failed: {e}") from e
        except Exception as e:  # network / unexpected SDK errors
            last_error = e
            break
    if response is None:
        raise AnalysisError(f"Deepgram transcription failed: {last_error}") from last_error

    data = _to_dict(response)
    if "results" not in data:
        # ListenV1AcceptedResponse (callback mode) — should not happen here
        raise AnalysisError(f"Unexpected Deepgram response shape: {list(data.keys())}")
    return _parse_response(data, model=model, warnings=warnings)


def _to_dict(response: Any) -> Dict[str, Any]:
    if hasattr(response, "model_dump"):
        return response.model_dump()
    if hasattr(response, "dict"):
        return response.dict()
    return dict(response)


def _parse_response(data: Dict[str, Any], model: str, warnings: List[str]) -> STTResult:
    results = data.get("results") or {}
    metadata = data.get("metadata") or {}

    channels = results.get("channels") or []
    alternative: Dict[str, Any] = {}
    if channels and (channels[0].get("alternatives") or []):
        alternative = channels[0]["alternatives"][0]

    words = [
        Word(
            word=w.get("word") or "",
            start=float(w.get("start") or 0.0),
            end=float(w.get("end") or 0.0),
            confidence=float(w.get("confidence") or 0.0),
            speaker=w.get("speaker"),
            punctuated_word=w.get("punctuated_word"),
        )
        for w in (alternative.get("words") or [])
    ]

    utterances = [
        Utterance(
            speaker=u.get("speaker"),
            start=float(u.get("start") or 0.0),
            end=float(u.get("end") or 0.0),
            text=u.get("transcript") or "",
            confidence=float(u.get("confidence") or 0.0),
        )
        for u in (results.get("utterances") or [])
        if (u.get("transcript") or "").strip()
    ]
    if not utterances and words:
        utterances = _utterances_from_words(words)
        warnings.append("Deepgram returned no utterances; synthesized them from word timings.")

    _attach_sentiment(utterances, words, results.get("sentiments") or {})

    topics = _collect_segment_labels(results.get("topics"), "topics", "topic")
    intents = _collect_segment_labels(results.get("intents"), "intents", "intent")

    summary = None
    summary_block = results.get("summary") or {}
    if isinstance(summary_block, dict):
        summary = summary_block.get("short") or summary_block.get("result")

    language = None
    model_info = metadata.get("model_info") or {}
    if isinstance(model_info, dict):
        for info in model_info.values():
            if isinstance(info, dict) and info.get("language"):
                language = info["language"]
                break

    return STTResult(
        model=model,
        duration=float(metadata.get("duration") or 0.0),
        language=language,
        words=words,
        utterances=utterances,
        topics=topics,
        intents=intents,
        summary=summary,
        warnings=warnings,
    )


def _utterances_from_words(words: List[Word]) -> List[Utterance]:
    """Group consecutive same-speaker words into utterances (fallback path)."""
    utterances: List[Utterance] = []
    run: List[Word] = []

    def flush():
        if not run:
            return
        utterances.append(
            Utterance(
                speaker=run[0].speaker,
                start=run[0].start,
                end=run[-1].end,
                text=" ".join(w.punctuated_word or w.word for w in run),
                confidence=sum(w.confidence for w in run) / len(run),
            )
        )

    for w in words:
        if run and w.speaker != run[-1].speaker:
            flush()
            run = []
        run.append(w)
    flush()
    return utterances


def _attach_sentiment(
    utterances: List[Utterance], words: List[Word], sentiments: Dict[str, Any]
) -> None:
    """Deepgram sentiment segments cover word-index ranges; map each utterance to
    the dominant sentiment of its word span."""
    segments = sentiments.get("segments") or []
    if not segments or not words:
        return
    # sentiment (label, score) per global word index
    word_sentiment: List[Optional[tuple]] = [None] * len(words)
    for seg in segments:
        label = seg.get("sentiment")
        score = seg.get("sentiment_score")
        if label is None:
            continue
        start_i = int(seg.get("start_word") or 0)
        end_i = int(seg.get("end_word") if seg.get("end_word") is not None else start_i)
        for i in range(max(0, start_i), min(len(words), end_i + 1)):
            word_sentiment[i] = (label, float(score or 0.0))

    for utt in utterances:
        span = [
            ws
            for w, ws in zip(words, word_sentiment)
            if ws is not None and utt.start <= w.start < utt.end + 1e-6
        ]
        if not span:
            continue
        labels = [s[0] for s in span]
        utt.sentiment = max(set(labels), key=labels.count)
        utt.sentiment_score = sum(s[1] for s in span) / len(span)


def _collect_segment_labels(block: Any, list_key: str, label_key: str) -> List[str]:
    """Flatten Deepgram topics/intents segments into a unique ordered label list.
    Tolerates both response shapes: {segments: [...]} and {results: {topics: {segments: [...]}}}."""
    labels: List[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for seg in node.get("segments") or []:
                for item in (seg.get(list_key) or []) if isinstance(seg, dict) else []:
                    label = item.get(label_key) if isinstance(item, dict) else None
                    if label and label not in labels:
                        labels.append(label)
            for value in node.values():
                if isinstance(value, (dict, list)):
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(block)
    return labels
