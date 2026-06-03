#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

from dotenv import load_dotenv
from loguru import logger
# Use pipecat.runner.types so we get the same classes as run.py (avoids isinstance mismatch)
from pipecat.runner.types import RunnerArguments
from pipecat.transports.base_transport import BaseTransport

from core.utils.telephony import provider_call_id

load_dotenv(override=True)


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    """Resolve the agent for this call, build its pipeline params, and run the pipeline.

    Telephony-only: the call must map to an agent (passed in `body['agent']` or resolved by
    the called number). There is no env-based fallback — an unresolved agent is an error.
    """
    from core.database.session import get_db_context
    from core.logging import start_call_trace
    from core.services.agent_runner_service import AgentRunnerService
    from core.services.pipeline import get_engine

    body = getattr(runner_args, "body", None) or {}
    with get_db_context() as db:
        agent = AgentRunnerService(db).get_agent_for_call(body)
    if not agent:
        raise ValueError(
            "No agent for this call: body['agent'] is empty and no agent maps to the called number."
        )
    start_call_trace(agent_id=agent.id, call_id=provider_call_id(body.get("call_data") or {}))
    logger.info(f"Running bot with agent config: id={agent.id} name={agent.name}")

    # PipelineParams.load picks prefetch-vs-DB and closes the session before the long call.
    engine = get_engine()
    params = engine.params_cls.load(agent, body)

    builder = engine.builder_cls(params)
    runner = engine.runner_cls(params, builder, transport, agent=agent, runner_args=runner_args)
    await runner.run()


async def bot(runner_args: RunnerArguments):
    """Main bot entry point compatible with Pipecat Cloud.

    Selects the call transport (telephony WebSocket / Daily / SmallWebRTC) via the
    transport registry, then runs the pipeline for the resolved agent.
    """
    # Establish one trace_id for the whole call as the very first thing, so every
    # subsequent log line carries it; the agent_id/call_id segments are filled in
    # once known (in the transport or run_bot). Logging-only — does not affect call flow.
    from core.logging import start_call_trace
    from core.services.transport import build_transport

    start_call_trace()

    transport = await build_transport(runner_args)
    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
