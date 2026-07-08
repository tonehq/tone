"""Input loading for call analysis: local files or a call id (DB + R2)."""

import io
import json
import uuid as uuid_lib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from core.services.call_analysis.errors import InputError

_MIME_BY_EXT = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".mp4": "audio/mp4",
    ".ogg": "audio/ogg",
    ".webm": "audio/webm",
    ".flac": "audio/flac",
}

_VALID_ROLES = {"user", "assistant"}


@dataclass
class CallInputs:
    audio_bytes: bytes
    audio_mime: str
    live_transcript: Optional[List[dict]]
    call_info: Optional[Dict[str, Any]]
    source: Dict[str, Any]
    warnings: List[str] = field(default_factory=list)


def load_from_files(audio_path: str, transcript_path: Optional[str] = None) -> CallInputs:
    audio_file = Path(audio_path)
    if not audio_file.is_file():
        raise InputError(f"Audio file not found: {audio_path}")
    audio_bytes = audio_file.read_bytes()
    if not audio_bytes:
        raise InputError(f"Audio file is empty: {audio_path}")
    mime = _MIME_BY_EXT.get(audio_file.suffix.lower())
    warnings: List[str] = []
    if mime is None:
        audio_bytes, mime = normalize_audio(audio_bytes, audio_file.suffix.lstrip("."))
        warnings.append(
            f"Unrecognized audio extension '{audio_file.suffix}' — converted to 16kHz mono WAV."
        )

    transcript = None
    if transcript_path:
        transcript_file = Path(transcript_path)
        if not transcript_file.is_file():
            raise InputError(f"Transcript file not found: {transcript_path}")
        try:
            raw = json.loads(transcript_file.read_text())
        except json.JSONDecodeError as e:
            raise InputError(f"Transcript is not valid JSON: {e}") from e
        transcript, transcript_warnings = validate_transcript(raw)
        warnings.extend(transcript_warnings)

    return CallInputs(
        audio_bytes=audio_bytes,
        audio_mime=mime,
        live_transcript=transcript,
        call_info=None,
        source={"mode": "local", "audio": str(audio_file), "transcript": transcript_path},
        warnings=warnings,
    )


def load_from_call_id(call_id: str) -> CallInputs:
    # Imported lazily so local-file mode works without DB/R2 configuration.
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from core.models.call import Call
    from core.models.upload import Upload
    from core.services.r2_storage_service import R2StorageService
    from shared.config import settings

    try:
        call_uuid = uuid_lib.UUID(call_id)
    except ValueError as e:
        raise InputError(f"Invalid call id (not a UUID): {call_id}") from e

    if not settings.DATABASE_URL:
        raise InputError("DATABASE_URL is not configured — required for --call-id mode.")

    engine = create_engine(settings.DATABASE_URL)
    session = sessionmaker(bind=engine)()
    try:
        call = session.query(Call).filter(Call.id == call_uuid).first()
        if call is None:
            raise InputError(f"Call not found: {call_id}")

        metadata = call.metadata_ or {}
        transcript = None
        warnings: List[str] = []
        raw_transcript = metadata.get("transcript")
        if raw_transcript:
            transcript, transcript_warnings = validate_transcript(raw_transcript)
            warnings.extend(transcript_warnings)
        else:
            warnings.append("Call has no stored transcript — cross-check will be skipped.")

        if not call.recording_upload_id:
            raise InputError(
                f"Call {call_id} has no recording. Provide the audio directly with --audio."
            )
        upload = session.query(Upload).filter(Upload.id == call.recording_upload_id).first()
        if upload is None or not upload.file_path:
            raise InputError(f"Recording upload row missing for call {call_id}.")

        try:
            audio_bytes = R2StorageService().download_file(upload.file_path)
        except Exception as e:
            raise InputError(
                f"Failed to download recording from R2 (key={upload.file_path}): {e}"
            ) from e

        call_info = {
            "call_id": str(call.id),
            "agent_id": str(call.agent_id),
            "direction": call.direction,
            "started_at": call.started_at.isoformat() if call.started_at else None,
            "ended_at": call.ended_at.isoformat() if call.ended_at else None,
            "duration_seconds": call.duration_seconds,
            "recording_duration_seconds": call.recording_duration_seconds,
            "provider_call_id": call.provider_call_id,
        }
        return CallInputs(
            audio_bytes=audio_bytes,
            audio_mime="audio/mpeg",  # recordings are encoded as MP3 by the pipeline
            live_transcript=transcript,
            call_info=call_info,
            source={"mode": "call_id", "call_id": call_id, "r2_key": upload.file_path},
            warnings=warnings,
        )
    finally:
        session.close()
        engine.dispose()


def validate_transcript(raw: Any) -> Tuple[List[dict], List[str]]:
    """Accepts a raw list or a {"transcript": [...]} wrapper. Returns normalized
    entries plus warnings; raises InputError on structural problems."""
    if isinstance(raw, dict) and isinstance(raw.get("transcript"), list):
        raw = raw["transcript"]
    if not isinstance(raw, list):
        raise InputError(
            "Transcript must be a JSON list of {role, text} entries "
            "(or an object with a 'transcript' list)."
        )

    warnings: List[str] = []
    entries: List[dict] = []
    skipped_roles: set = set()
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise InputError(f"Transcript entry {i} is not an object: {entry!r}")
        role = entry.get("role")
        text = entry.get("text")
        if role is None or text is None:
            raise InputError(f"Transcript entry {i} is missing 'role' or 'text': {entry!r}")
        if not isinstance(text, str):
            raise InputError(f"Transcript entry {i} has a non-string 'text': {entry!r}")
        if role not in _VALID_ROLES:
            skipped_roles.add(role)
            continue
        if not text.strip():
            continue
        entries.append({"role": role, "text": text, "timestamp": entry.get("timestamp")})

    if skipped_roles:
        warnings.append(
            f"Ignored transcript entries with non user/assistant roles: {sorted(skipped_roles)}"
        )
    if not entries:
        warnings.append("Transcript contained no usable entries — treated as unavailable.")
        return [], warnings
    return entries, warnings


def normalize_audio(audio_bytes: bytes, fmt: Optional[str] = None) -> Tuple[bytes, str]:
    """Convert arbitrary audio to 16kHz mono WAV via pydub (mirrors the pipeline's
    recording format). Raises InputError if the audio can't be decoded."""
    from pydub import AudioSegment

    try:
        segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format=fmt or None)
    except Exception as e:
        raise InputError(f"Could not decode audio ({fmt or 'unknown format'}): {e}") from e
    segment = segment.set_channels(1).set_frame_rate(16000)
    buffer = io.BytesIO()
    segment.export(buffer, format="wav")
    logger.info("Normalized audio to 16kHz mono WAV ({} bytes)", buffer.getbuffer().nbytes)
    return buffer.getvalue(), "audio/wav"
