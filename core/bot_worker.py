"""Subprocess entry point for isolated telephony bot execution.

Receives agent_id, transport_type, call_data, and port as CLI args.
Starts a minimal FastAPI/uvicorn server on the given port with a /ws endpoint.
On WebSocket connection: loads Agent from DB, constructs WebSocketRunnerArguments,
and calls the existing bot() function.
"""

import argparse
import asyncio
import json
import sys

from loguru import logger


def main():
    parser = argparse.ArgumentParser(description="Bot Worker Subprocess")
    parser.add_argument("--agent_id", type=str, required=True, help="Agent UUID")
    parser.add_argument("--transport_type", type=str, required=True, help="Telephony provider type")
    parser.add_argument("--call_data", type=str, required=True, help="JSON-encoded call data")
    parser.add_argument("--port", type=int, required=True, help="Local WebSocket port")
    args = parser.parse_args()

    call_data = json.loads(args.call_data)

    import uvicorn
    from fastapi import FastAPI, WebSocket

    app = FastAPI()

    @app.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket):
        await websocket.accept()
        logger.info(
            "Bot worker subprocess connected: agent_id=%s transport_type=%s port=%d",
            args.agent_id,
            args.transport_type,
            args.port,
        )

        try:
            from core.database.session import get_db_context
            from core.models.agent import Agent
            from pipecat.runner.types import WebSocketRunnerArguments

            with get_db_context() as db:
                agent = db.query(Agent).filter(Agent.id == args.agent_id).first()
                if not agent:
                    logger.error("Agent not found: %s", args.agent_id)
                    await websocket.close(code=1011, reason="Agent not found")
                    return
                # Detach from session so it can be used after context closes
                db.expunge(agent)

            body = {
                "call_data": call_data,
                "transport_type": args.transport_type,
                "agent_id": args.agent_id,
                "agent": agent,
            }

            runner_args = WebSocketRunnerArguments(websocket=websocket, body=body)

            from core.bot import bot

            await bot(runner_args)
        except Exception:
            logger.exception("Bot worker subprocess error")
        finally:
            logger.info("Bot worker subprocess finished: agent_id=%s", args.agent_id)

    # Signal readiness to the parent process via stdout
    @app.on_event("startup")
    async def on_startup():
        print(f"WORKER_READY:{args.port}", flush=True)

    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
