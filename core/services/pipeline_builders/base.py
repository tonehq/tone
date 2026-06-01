from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from loguru import logger


@dataclass
class BuildContext:
    provider_name: str
    api_key: Optional[str]
    model: Optional[str]
    metadata: dict
    model_meta: dict
    voice_id: Optional[str] = None
    language: Optional[str] = None
    session: Optional[Any] = None


# Structural metadata keys that are never InputParams fields. These are
# resolved by BuildContext / builders directly and excluded from
# build_input_params to avoid noise.
_STRUCTURAL_KEYS = {
    "provider_id", "model_id", "model", "voice_id",
    "is_s2s", "system_prompt", "system_instruction", "base_url",
}


def _clean_metadata_value(value: Any) -> Any:
    """Sanitize a metadata value from the frontend form.
    Returns None for empty/null-ish values so builders can skip them."""
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped in ("", "None", "null", "undefined"):
            return None
        return stripped
    return value


def clean_meta(metadata: dict, key: str) -> Any:
    """Get a cleaned metadata value. Use this in builders instead of
    raw ctx.metadata.get() to handle form-submitted nullish values."""
    return _clean_metadata_value(metadata.get(key))


def resolve_language_code(value: Any) -> Optional[str]:
    """Convert a language value to a valid Pipecat Language enum code.
    Handles display names (e.g. 'English' → 'en'), codes ('en' → 'en'),
    and returns None for invalid/empty values."""
    cleaned = _clean_metadata_value(value)
    if not cleaned:
        return None
    # If it looks like a BCP-47 code (lowercase, with optional region), use as-is
    if cleaned == cleaned.lower() or "-" in cleaned:
        return cleaned
    # Try to resolve display name → code via Pipecat's Language enum
    try:
        from pipecat.transcriptions.language import Language
        # Search enum by name match (case-insensitive)
        lower = cleaned.lower()
        for lang in Language:
            if lang.name.lower() == lower or lang.value.lower() == lower:
                return lang.value
    except ImportError:
        pass
    # Fallback: if it's a capitalized display name, try common mappings
    _COMMON = {
        "english": "en", "spanish": "es", "french": "fr", "german": "de",
        "italian": "it", "portuguese": "pt", "dutch": "nl", "russian": "ru",
        "chinese": "zh", "japanese": "ja", "korean": "ko", "arabic": "ar",
        "hindi": "hi", "turkish": "tr", "polish": "pl", "swedish": "sv",
        "danish": "da", "norwegian": "nb", "finnish": "fi", "greek": "el",
        "czech": "cs", "romanian": "ro", "hungarian": "hu", "thai": "th",
        "vietnamese": "vi", "indonesian": "id", "malay": "ms", "tamil": "ta",
        "telugu": "te", "bengali": "bn", "gujarati": "gu", "kannada": "kn",
        "marathi": "mr", "punjabi": "pa", "urdu": "ur",
    }
    mapped = _COMMON.get(cleaned.lower())
    if mapped:
        return mapped
    return None


def build_input_params(service_class: Any, metadata: dict) -> Any:
    input_params_class = getattr(service_class, "InputParams", None)
    if not input_params_class:
        return None
    valid_keys = set(input_params_class.model_fields.keys()) - _STRUCTURAL_KEYS
    filtered = {k: v for k, v in metadata.items() if k in valid_keys and v is not None and v != "None" and v != ""}
    for k, v in filtered.items():
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, (list, dict)):
                    filtered[k] = parsed
            except (json.JSONDecodeError, TypeError):
                pass
    if not filtered:
        logger.debug(f"[build_input_params] {service_class.__name__}: no matching params in metadata, using defaults")
        return input_params_class()
    try:
        params = input_params_class(**filtered)
        logger.info(f"[build_input_params] {service_class.__name__}: applied {filtered} → {params}")
        return params
    except Exception as e:
        logger.warning(f"Failed to build InputParams for {service_class.__name__}: {e}")
        return input_params_class()


class ServiceBuilder(ABC):
    @abstractmethod
    def build(self, ctx: BuildContext) -> Any:
        ...


class LLMBuilder(ServiceBuilder):
    @abstractmethod
    def build(self, ctx: BuildContext) -> Any:
        ...


class STTBuilder(ServiceBuilder):
    @abstractmethod
    def build(self, ctx: BuildContext) -> Any:
        ...


class TTSBuilder(ServiceBuilder):
    @abstractmethod
    def build(self, ctx: BuildContext) -> Any:
        ...
