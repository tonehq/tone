"""Pipeline params layer: base + Pipecat child."""

from core.services.pipeline.params.base import PipelineParams, ServiceSpec
from core.services.pipeline.params.pipecat import PipecatPipelineParams

__all__ = ["PipelineParams", "ServiceSpec", "PipecatPipelineParams"]
