"""Pipecat-specific pipeline params.

Currently a typed marker over the framework-agnostic `PipelineParams`. Any Pipecat-only
param resolution (e.g. enum mappings that belong to params rather than service construction)
should live here so the base class stays framework-agnostic. The live TTS sample-rate and
Rime `Language` resolution intentionally stay in the builder, since they need the
constructed service instance.
"""

from dataclasses import dataclass

from core.services.pipeline.params.base import PipelineParams


@dataclass
class PipecatPipelineParams(PipelineParams):
    """PipelineParams specialized for the Pipecat builder/runner."""

    pass
