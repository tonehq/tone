"""Public telephony WebSocket endpoint — no authentication required.

Telephony providers (Twilio, Telnyx, Exotel, Plivo) connect here to stream
audio for voice agent calls. The endpoint accepts the WebSocket, resolves the
agent by phone number, and runs the voice pipeline.
"""

import os

from fastapi import APIRouter, WebSocket
from loguru import logger

router = APIRouter()


@router.websocket("/ws")
async def telephony_websocket(websocket: WebSocket):
    """Handle incoming telephony WebSocket connections.

    Accepts the WebSocket and:
    1. Parses the first telephony messages to identify the provider and call data
    2. Resolves the agent by the 'to' phone number via BotRunnerService
    3. Optionally spawns a subprocess bot if USE_SUBPROCESS_BOT=true
    4. Creates WebSocketRunnerArguments and runs the voice pipeline via bot()
    """
    await websocket.accept()
    logger.info("Telephony WebSocket connection accepted")

    from core.bot import bot
    from core.database.session import get_db_context
    from core.services.bot_runner_service import BotRunnerService
    from pipecat.runner.types import WebSocketRunnerArguments

    body = {}
    try:
        with get_db_context() as db:
            agent, transport_type, call_data = await BotRunnerService(
                db
            ).get_bot_for_incoming_call(websocket)

        # Check if subprocess mode is enabled
        use_subprocess = os.environ.get("USE_SUBPROCESS_BOT", "false").lower() == "true"
        if use_subprocess and agent is not None:
            logger.info(
                "Subprocess mode enabled — launching bot worker for agent_id=%s",
                agent.id,
            )
            try:
                from core.services.subprocess_bot_manager import SubprocessBotManager

                await SubprocessBotManager.launch(
                    websocket=websocket,
                    agent_id=str(agent.id),
                    transport_type=transport_type,
                    call_data=call_data,
                )
                return
            except Exception as e:
                logger.error(
                    "Subprocess bot launch failed, falling back to in-process: %s", e
                )

        body = {
            "call_data": call_data,
            "transport_type": transport_type,
            "agent_id": agent.id if agent else None,
            "agent": agent,
        }

    except Exception as e:
        logger.warning(
            "Bot runner service failed, calling bot without pre-parsed data: %s", e
        )

    runner_args = WebSocketRunnerArguments(websocket=websocket, body=body)
    await bot(runner_args)
