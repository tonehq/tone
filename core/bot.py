#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import asyncio

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
    from core.logging import get_applied_level, setup_logging, start_call_trace
    from core.services.agent_runner_service import AgentRunnerService
    from core.services.log_level_resolver import resolve_call_log_level
    from core.services.pipeline import get_engine
    from sqlalchemy.exc import SQLAlchemyError

    body = getattr(runner_args, "body", None) or {}
    call_log_level = None
    call_log_level_source = None
    try:
        with get_db_context() as db:
            agent = AgentRunnerService(db).get_agent_for_call(body)
            if agent is not None:
                # Single place that reads the log_level columns (agent > org > env).
                # Safe in the prefetch subprocess: a transient agent skips the org query.
                call_log_level, call_log_level_source = resolve_call_log_level(db, agent=agent)
    except SQLAlchemyError:
        logger.exception("[bot] database error resolving agent for call")
        raise
    if not agent:
        logger.error(
            "[bot] no agent for this call — body['agent'] empty and no agent maps to the called number"
        )
        raise ValueError(
            "No agent for this call: body['agent'] is empty and no agent maps to the called number."
        )
    # Apply the resolved per-call log level for the rest of this call. In a call
    # subprocess this scopes to exactly one call; in the shared-process dev path it
    # applies process-wide for the call's duration.
    if call_log_level and call_log_level != get_applied_level():
        setup_logging(level=call_log_level)
        logger.info(
            "[bot] applied log level {} (source={}) for this call",
            call_log_level, call_log_level_source,
        )
    start_call_trace(agent_id=agent.id, call_id=provider_call_id(body.get("call_data") or {}))
    logger.info(f"Running bot with agent config: id={agent.id} name={agent.name}")

    # PipelineParams.load picks prefetch-vs-DB and closes the session before the long call.
    engine = get_engine()
    params = engine.params_cls.load(agent, body)
    logger.info("[bot] pipeline params loaded (engine={}) — building pipeline", type(engine).__name__)

    builder = engine.builder_cls(params)
    runner = engine.runner_cls(params, builder, transport, agent=agent, runner_args=runner_args)
    logger.info("[bot] pipeline built — starting runner for agent id={}", agent.id)
    try:
        await runner.run()
    finally:
        logger.info("[bot] pipeline runner finished for agent id={}", agent.id)


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

    # Outer backstop for the whole call. Pipeline-runtime failures are already
    # logged (with fail_call) inside the runner; this catches everything else
    # (transport build, params/engine setup, agent resolution) so no call dies
    # without a traceback. CancelledError is normal teardown — never swallow it.
    try:
        transport = await build_transport(runner_args)
        await run_bot(transport, runner_args)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("[bot] call failed")
        raise


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
