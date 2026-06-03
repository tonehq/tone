"""Framework-agnostic pipeline runner interface."""

from typing import Any

from core.services.pipeline.builder.base import PipelineBuilder
from core.services.pipeline.params.base import PipelineParams


class PipelineRunner:
    """Runs a built pipeline and manages the call lifecycle. Subclass per framework."""

    def __init__(
        self,
        params: PipelineParams,
        builder: PipelineBuilder,
        transport: Any,
        agent: Any = None,
        runner_args: Any = None,
    ):
        self.params = params
        self.builder = builder
        self.transport = transport
        self.agent = agent
        self.runner_args = runner_args

    async def run(self) -> None:
        raise NotImplementedError
