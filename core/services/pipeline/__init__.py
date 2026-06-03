"""Voice pipeline package.

Three-layer architecture, each with a framework-agnostic base + a Pipecat child:

    params  -> PipelineParams / PipecatPipelineParams   (config: services + messages + flags)
    builder -> PipelineBuilder / PipecatPipelineBuilder  (build services + assemble pipeline)
    runner  -> PipelineRunner / PipecatPipelineRunner    (run + lifecycle: call log, recording)

Two supporting modules sit under the params/builder layers:

    service_resolver -> reads the DB + decrypts keys into service specs (the only DB access)
    service_factory  -> constructs Pipecat services from those specs (pure, no DB)

`PipelineParams.from_agent(agent, db)` is the single source of truth that reads the agent
config, decrypts provider keys, and produces the params consumed by the builder.
"""

from core.services.pipeline.builder import (BuildResult, PipecatPipelineBuilder,
                                             PipelineBuilder)
from core.services.pipeline.engine import (DEFAULT_ENGINE, PipelineEngine,
                                           get_engine, register_engine)
from core.services.pipeline.params import (PipecatPipelineParams,
                                           PipelineParams)
from core.services.pipeline.runner import PipecatPipelineRunner, PipelineRunner

# Register the built-in Pipecat engine. New engines register their own trio the same way.
register_engine(
    PipelineEngine(
        name="pipecat",
        params_cls=PipecatPipelineParams,
        builder_cls=PipecatPipelineBuilder,
        runner_cls=PipecatPipelineRunner,
    )
)

__all__ = [
    "PipelineParams",
    "PipecatPipelineParams",
    "PipelineBuilder",
    "PipecatPipelineBuilder",
    "BuildResult",
    "PipelineRunner",
    "PipecatPipelineRunner",
    "PipelineEngine",
    "get_engine",
    "register_engine",
    "DEFAULT_ENGINE",
]
