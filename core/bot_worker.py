"""Subprocess entry point for isolated telephony bot execution.

Receives agent_id, transport_type, call_data as CLI args.
Communicates with the parent process via stdin/stdout pipes using a
lightweight binary framing protocol (see core.services.pipe_ipc).

No FastAPI or uvicorn — the PipeWebSocket adapter provides the same
interface that FastAPIWebsocketTransport expects.

If --agent_data is provided, the Agent object is reconstructed from it
without any DB query — saving ~4-5s of subprocess DB connection time.
"""

import argparse
import asyncio
import json
import os
import time as _time
import uuid as _uuid

from loguru import logger


def _reconstruct_agent(agent_data: dict):
    """Reconstruct an Agent ORM instance from serialized data without DB.

    Creates a transient (not attached to any session) Agent object with
    the fields the pipeline needs: id, uuid, name, organization_id, etc.
    """
    from core.models.agent import Agent
    from core.models.enums import AgentType

    agent = Agent(
        id=agent_data["id"],
        uuid=_uuid.UUID(agent_data["uuid"]) if agent_data.get("uuid") else None,
        name=agent_data.get("name"),
        organization_id=_uuid.UUID(agent_data["organization_id"]) if agent_data.get("organization_id") else None,
        description=agent_data.get("description"),
        status=agent_data.get("status"),
        agent_type=AgentType[agent_data["agent_type"]] if agent_data.get("agent_type") else None,
        meta_data=agent_data.get("meta_data"),
        log_level=agent_data.get("log_level"),
        created_at=agent_data.get("created_at"),
        updated_at=agent_data.get("updated_at"),
    )
    # Make it transient — not pending insertion into any session
    from sqlalchemy.orm import make_transient
    make_transient(agent)

    return agent


async def _async_main(bot_fn, WSRunnerArgs, agent, agent_id, transport_type, call_data, prefetched_services, ipc_write_fd):
    """Run the bot pipeline using pipe-based IPC instead of FastAPI/uvicorn."""
    from core.services.pipe_ipc import PipeWebSocket, create_stdin_reader, signal_pipe_ready

    reader = await create_stdin_reader()
    pipe_ws = PipeWebSocket(reader, ipc_write_fd)

    # Signal ready to parent — parent starts relaying frames after this
    signal_pipe_ready(ipc_write_fd)
    logger.info(
        "Bot worker pipe ready: agent_id=%s transport_type=%s",
        agent_id,
        transport_type,
    )

    # One trace_id for the whole subprocess call so every log line carries it.
    # Honors an externally-supplied _trace_id, else generates one. Logging-only.
    from core.logging import start_call_trace
    from core.utils.telephony import provider_call_id
    start_call_trace(
        agent_id=agent_id,
        call_id=provider_call_id(call_data),
        external=call_data.get("_trace_id"),
    )

    try:
        body = {
            "call_data": call_data,
            "transport_type": transport_type,
            "agent_id": agent_id,
            "agent": agent,
            "_prefetched_services": prefetched_services,
        }
        runner_args = WSRunnerArgs(websocket=pipe_ws, body=body)
        await bot_fn(runner_args)
    except Exception:
        logger.exception("Bot worker pipe error")
    finally:
        try:
            os.close(ipc_write_fd)
        except OSError:
            pass
        logger.info("Bot worker subprocess finished: agent_id=%s", agent_id)


def main():
    parser = argparse.ArgumentParser(description="Bot Worker Subprocess")
    parser.add_argument("--agent_id", type=str, required=True, help="Agent UUID")
    parser.add_argument("--transport_type", type=str, required=True, help="Telephony provider type")
    parser.add_argument("--call_data", type=str, required=True, help="JSON-encoded call data")
    parser.add_argument("--agent_data", type=str, required=False, help="JSON-encoded agent fields (skips DB query)")
    args = parser.parse_args()

    call_data = json.loads(args.call_data)

    # Configure loguru with trace_id format for subprocess
    from core.logging import setup_logging
    setup_logging()

    # --- Redirect stdout to stderr FIRST (before any imports that might print) ---
    from core.services.pipe_ipc import setup_subprocess_ipc
    ipc_write_fd = setup_subprocess_ipc()

    # --- Heavy imports (safe — any print() goes to stderr now) ---
    _t = _time.monotonic()
    from pipecat.runner.types import WebSocketRunnerArguments
    from core.bot import bot
    logger.info("[TIMING] bot_worker imports done (+%.3fs)", _time.monotonic() - _t)

    # --- Reconstruct agent from passed data OR fall back to DB query ---
    _t = _time.monotonic()
    prefetched_services = None
    if args.agent_data:
        agent_data = json.loads(args.agent_data)
        prefetched_services = agent_data.pop("_prefetched_services", None)
        agent = _reconstruct_agent(agent_data)
        logger.info("[TIMING] bot_worker agent reconstructed from passed data (+%.3fs)", _time.monotonic() - _t)
    else:
        from core.database.session import get_db_context
        from core.models.agent import Agent

        with get_db_context() as db:
            agent = db.query(Agent).filter(Agent.id == args.agent_id).first()
            if agent:
                db.expunge(agent)
        logger.info("[TIMING] bot_worker agent query from DB (+%.3fs)", _time.monotonic() - _t)

    if not agent:
        logger.error("Agent not found: %s — subprocess exiting", args.agent_id)
        os.close(ipc_write_fd)
        return

    # --- Run bot with pipe IPC (no FastAPI/uvicorn needed) ---
    asyncio.run(
        _async_main(
            bot, WebSocketRunnerArguments, agent,
            args.agent_id, args.transport_type, call_data,
            prefetched_services, ipc_write_fd,
        )
    )


if __name__ == "__main__":
    main()
