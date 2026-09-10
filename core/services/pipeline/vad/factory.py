from typing import Any, Dict, List, Optional, Type

from pipecat.audio.vad.vad_analyzer import VADAnalyzer, VADParams

from core.services.meta_data_schema_validator import MetaDataSchemaValidator, coerce_settings
from core.services.pipeline.vad.aic_quail import AICQuailVADProvider
from core.services.pipeline.vad.base import VADProvider
from core.services.pipeline.vad.silero import SileroVADProvider
from core.services.pipeline.vad.ten import TENVADProvider

VAD_PROVIDERS: Dict[str, Type[VADProvider]] = {
    cls.slug: cls for cls in (SileroVADProvider, TENVADProvider, AICQuailVADProvider)
}

DEFAULT_VAD_PROVIDER = SileroVADProvider.slug

PROVIDER_KEY = "provider"


def _provider_class(raw: Optional[dict]) -> Type[VADProvider]:
    slug = (raw or {}).get(PROVIDER_KEY) or DEFAULT_VAD_PROVIDER
    try:
        return VAD_PROVIDERS[slug]
    except KeyError:
        raise ValueError(f"Unknown VAD provider: {slug!r}. Available: {sorted(VAD_PROVIDERS)}")


def get_vad_provider(raw: Optional[dict]) -> VADProvider:
    cls = _provider_class(raw)
    return cls(coerce_settings(cls.schema, raw or {}))


def build_vad_analyzer(raw: Optional[dict], params: VADParams) -> VADAnalyzer:
    return get_vad_provider(raw).build(params)


def available_vad_providers() -> Dict[str, Type[VADProvider]]:
    return {slug: cls for slug, cls in VAD_PROVIDERS.items() if cls.available()}


def list_vad_providers() -> List[dict]:
    return [
        {
            "id": cls.slug,
            "display_name": cls.display_name,
            "description": cls.description,
            "meta_data_schema": cls.schema,
        }
        for cls in available_vad_providers().values()
    ]


def validate_vad_provider(raw: Any) -> Dict[str, List[str]]:
    if not isinstance(raw, dict):
        return {PROVIDER_KEY: ["vad must be an object"]}
    slug = raw.get(PROVIDER_KEY) or DEFAULT_VAD_PROVIDER
    available = available_vad_providers()
    cls = available.get(slug)
    if cls is None:
        return {PROVIDER_KEY: [f"provider must be one of: {', '.join(available)}"]}
    return MetaDataSchemaValidator().validate_settings(cls.schema, raw)
