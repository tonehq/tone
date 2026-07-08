"""Orchestrator for call analysis — the reusable entry point.

No CLI or HTTP coupling: tomorrow's post-call worker calls exactly
`analyze_call(load_from_call_id(call_id), AnalysisOptions(...))`.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from loguru import logger

from core.services.call_analysis.crosscheck import cross_check, map_speakers_to_roles
from core.services.call_analysis.errors import AnalysisError, MissingKeyError
from core.services.call_analysis.inputs import CallInputs, normalize_audio
from core.services.call_analysis.llm_layer import run_llm_analysis
from core.services.call_analysis.metrics import build_sentiment_timeline, compute_metrics
from core.services.call_analysis.schemas import AnalysisReport, STTSection
from core.services.call_analysis.stt_engine import transcribe


@dataclass
class AnalysisOptions:
    stt_model: str = "nova-3"
    run_llm: bool = False
    llm_provider: str = "auto"
    llm_model: Optional[str] = None
    dead_air_threshold: float = 3.0


async def analyze_call(
    inputs: CallInputs, options: Optional[AnalysisOptions] = None
) -> AnalysisReport:
    options = options or AnalysisOptions()
    report = AnalysisReport(
        generated_at=datetime.now(timezone.utc),
        source=inputs.source,
        call_info=inputs.call_info,
        warnings=list(inputs.warnings),
    )

    # 1. STT — the primary engine; failure here is fatal.
    logger.info("Transcribing audio ({} bytes, {})", len(inputs.audio_bytes), inputs.audio_mime)
    try:
        stt = await transcribe(
            inputs.audio_bytes, mime=inputs.audio_mime, model=options.stt_model
        )
    except AnalysisError:
        # One recovery attempt: re-encode the audio and retry (covers containers
        # Deepgram won't sniff correctly).
        logger.warning("Transcription failed — normalizing audio and retrying once")
        audio_bytes, mime = normalize_audio(inputs.audio_bytes, _fmt_from_mime(inputs.audio_mime))
        stt = await transcribe(audio_bytes, mime=mime, model=options.stt_model)
        report.warnings.append("Audio was re-encoded to 16kHz mono WAV before transcription.")
    report.warnings.extend(stt.warnings)

    if not stt.utterances:
        report.warnings.append("No speech detected in the recording.")

    expected = (inputs.call_info or {}).get("recording_duration_seconds")
    if expected and stt.duration and abs(stt.duration - expected) > max(5, 0.1 * expected):
        report.warnings.append(
            f"Audio duration ({stt.duration:.0f}s) differs from the recorded call "
            f"duration ({expected}s)."
        )

    # 2. Speaker → role mapping (needs the live transcript when available).
    role_map = map_speakers_to_roles(stt, inputs.live_transcript)
    for utt in stt.utterances:
        if utt.speaker is not None:
            utt.role = role_map.get(utt.speaker)

    report.stt = STTSection(
        model=stt.model,
        duration_seconds=round(stt.duration, 2),
        language=stt.language,
        full_transcript=" ".join(u.text for u in stt.utterances),
        utterances=stt.utterances,
        topics=stt.topics,
        intents=stt.intents,
        deepgram_summary=stt.summary,
    )

    # 3-5. Derived layers degrade gracefully — a failure never loses the report.
    try:
        report.metrics = compute_metrics(
            stt, role_map=role_map, dead_air_threshold=options.dead_air_threshold
        )
    except Exception as e:
        logger.exception("Metrics computation failed")
        report.skipped_layers.append(f"metrics: {e}")

    try:
        report.sentiment_timeline = build_sentiment_timeline(stt, role_map=role_map)
    except Exception as e:
        logger.exception("Sentiment timeline failed")
        report.skipped_layers.append(f"sentiment_timeline: {e}")

    try:
        report.crosscheck = cross_check(stt, inputs.live_transcript)
    except Exception as e:
        logger.exception("Transcript cross-check failed")
        report.skipped_layers.append(f"crosscheck: {e}")

    if options.run_llm:
        try:
            report.llm_analysis = await run_llm_analysis(
                stt,
                report.metrics,
                role_map=role_map,
                provider=options.llm_provider,
                model=options.llm_model,
            )
        except MissingKeyError as e:
            report.skipped_layers.append(f"llm: {e}")
        except Exception as e:
            logger.exception("LLM analysis failed")
            report.skipped_layers.append(f"llm: {e}")

    return report


def _fmt_from_mime(mime: str) -> Optional[str]:
    return {
        "audio/mpeg": "mp3",
        "audio/wav": "wav",
        "audio/mp4": "mp4",
        "audio/ogg": "ogg",
        "audio/webm": "webm",
        "audio/flac": "flac",
    }.get(mime)
