"""Warm worker subprocess — pre-imports heavy modules and waits for a call.

Lifecycle:
1. Import pipecat, core.bot, and all heavy dependencies
2. Signal WARM_READY:{port} on stdout
3. Wait for call data on stdin (JSON line)
4. Start FastAPI/uvicorn on the assigned port with a /ws endpoint
5. Handle one call, then exit

This is the warm equivalent of core/bot_worker.py. The key difference is
that imports happen at spawn time (during server startup), not when a call
arrives, saving ~2.9s per call.
"""

import argparse
import json
import sys
import time as _time
import uuid as _uuid

from loguru import logger


def _reconstruct_agent(agent_data: dict):
    """Reconstruct an Agent ORM instance from serialized data without DB."""
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
        created_at=agent_data.get("created_at"),
        updated_at=agent_data.get("updated_at"),
    )
    from sqlalchemy.orm import make_transient
    make_transient(agent)
    return agent


def main():
    parser = argparse.ArgumentParser(description="Warm Bot Worker")
    parser.add_argument("--port", type=int, required=True, help="Local WebSocket port")
    args = parser.parse_args()

    # --- Phase 1: Heavy imports upfront ---
    _t = _time.monotonic()
    import uvicorn
    from fastapi import FastAPI, WebSocket

    from pipecat.runner.types import WebSocketRunnerArguments
    from core.bot import bot
    logger.info("[TIMING] warm_worker imports done (+%.3fs)", _time.monotonic() - _t)

    # Signal that we're ready and waiting
    print(f"WARM_READY:{args.port}", flush=True)

    # --- Phase 2: Wait for call data on stdin ---
    logger.info("Warm worker pid=%d port=%d waiting for call data...", __import__("os").getpid(), args.port)
    line = sys.stdin.readline()
    if not line:
        logger.error("Warm worker: stdin closed before receiving call data")
        return

    _t = _time.monotonic()
    call_payload = json.loads(line.strip())

    agent_id = call_payload["agent_id"]
    transport_type = call_payload["transport_type"]
    call_data = call_payload["call_data"]
    agent_data = call_payload.get("agent_data")

    # --- Phase 3: Reconstruct agent (fast, no imports needed) ---
    prefetched_services = None
    if agent_data:
        prefetched_services = agent_data.pop("_prefetched_services", None)
        agent = _reconstruct_agent(agent_data)
        logger.info("[TIMING] warm_worker agent reconstructed (+%.3fs)", _time.monotonic() - _t)
    else:
        from core.database.session import get_db_context
        from core.models.agent import Agent as AgentModel

        with get_db_context() as db:
            agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
            if agent:
                db.expunge(agent)
        logger.info("[TIMING] warm_worker agent query from DB (+%.3fs)", _time.monotonic() - _t)

    if not agent:
        logger.error("Agent not found: %s — warm worker exiting", agent_id)
        return

    # --- Phase 4: Start FastAPI server and handle one call ---
    app = FastAPI()
    _ws_connected = False

    @app.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket):
        nonlocal _ws_connected
        await websocket.accept()
        if _ws_connected:
            logger.warning("Rejecting duplicate WS connection for agent_id=%s", agent_id)
            await websocket.close(code=1013, reason="Already connected")
            return
        _ws_connected = True
        logger.info(
            "Warm worker connected: agent_id=%s transport_type=%s port=%d",
            agent_id,
            transport_type,
            args.port,
        )

        try:
            body = {
                "call_data": call_data,
                "transport_type": transport_type,
                "agent_id": agent_id,
                "agent": agent,
                "_prefetched_services": prefetched_services,
            }

            runner_args = WebSocketRunnerArguments(websocket=websocket, body=body)
            await bot(runner_args)
        except Exception:
            logger.exception("Warm worker error")
        finally:
            _ws_connected = False
            logger.info("Warm worker finished: agent_id=%s", agent_id)

    @app.on_event("startup")
    async def on_startup():
        print(f"WORKER_READY:{args.port}", flush=True)

    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
