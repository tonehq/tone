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


def build_input_params(service_class: Any, metadata: dict) -> Any:
    input_params_class = getattr(service_class, "InputParams", None)
    if not input_params_class:
        return None
    valid_keys = set(input_params_class.model_fields.keys())
    filtered = {k: v for k, v in metadata.items() if k in valid_keys and v is not None and v != "None"}
    for k, v in filtered.items():
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, (list, dict)):
                    filtered[k] = parsed
            except (json.JSONDecodeError, TypeError):
                pass
    if not filtered:
        return input_params_class()
    try:
        return input_params_class(**filtered)
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
