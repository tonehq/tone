"""Pipeline engine selection.

An "engine" bundles the (params, builder, runner) trio for one pipeline implementation,
so callers select an engine *once* instead of hardcoding a concrete class. Today only
"pipecat" is registered; to add another engine (e.g. a different voice framework),
implement the three classes (subclassing the base params/builder/runner) and register
them here — no changes needed in bot.py or the telephony routers.
"""

from dataclasses import dataclass
from typing import Dict, Type

from core.services.pipeline.builder.base import PipelineBuilder
from core.services.pipeline.params.base import PipelineParams
from core.services.pipeline.runner.base import PipelineRunner

DEFAULT_ENGINE = "pipecat"


@dataclass(frozen=True)
class PipelineEngine:
    """The concrete params/builder/runner classes for one engine."""

    name: str
    params_cls: Type[PipelineParams]
    builder_cls: Type[PipelineBuilder]
    runner_cls: Type[PipelineRunner]


_REGISTRY: Dict[str, PipelineEngine] = {}


def register_engine(engine: PipelineEngine) -> None:
    _REGISTRY[engine.name] = engine


def get_engine(name: str = None) -> PipelineEngine:
    """Return the engine trio for `name` (defaults to DEFAULT_ENGINE)."""
    name = name or DEFAULT_ENGINE
    try:
        return _REGISTRY[name]
    except KeyError:
        raise ValueError(
            f"Unknown pipeline engine '{name}'. Registered engines: {sorted(_REGISTRY)}"
        )
