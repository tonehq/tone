"""Public telephony WebSocket endpoint — no authentication required.

Telephony providers (Twilio, Telnyx, Exotel, Plivo) connect here to stream
audio for voice agent calls. The endpoint accepts the WebSocket, resolves the
agent by phone number, and runs the voice pipeline.
"""

import os
import time as _time

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
    _t_ws_start = _time.monotonic()
    await websocket.accept()
    logger.info("[TIMING] WS accepted (+%.3fs)", _time.monotonic() - _t_ws_start)

    _t_import = _time.monotonic()
    from core.database.session import get_db_context
    from core.services.bot_runner_service import BotRunnerService
    logger.info("[TIMING] telephony.py imports done (+%.3fs)", _time.monotonic() - _t_import)

    body = {}
    try:
        _t_bot_runner = _time.monotonic()
        prefetched_services = None
        with get_db_context() as db:
            agent, transport_type, call_data = await BotRunnerService(
                db
            ).get_bot_for_incoming_call(websocket)

            # Pre-fetch service config + credentials + telephony creds in one DB session
            # so the subprocess doesn't need to establish its own DB connection
            if agent:
                # Store org_id in call_data so downstream code can fetch org-scoped creds
                call_data["_org_id"] = str(agent.organization_id) if agent.organization_id else None
                _t_prefetch = _time.monotonic()
                from core.services.agent_factory_service import AgentFactoryService
                factory = AgentFactoryService(db)
                # Pass transport_type so telephony creds are fetched in the same DB session
                prefetched_services = factory.serialize_agent_bot_data(agent, transport_type=transport_type)
                # Extract telephony creds from prefetched data into call_data
                if prefetched_services and "_telephony_creds" in prefetched_services:
                    telephony_creds = prefetched_services.pop("_telephony_creds")
                    if transport_type == "twilio" and "_twilio_creds" not in call_data:
                        call_data["_twilio_creds"] = telephony_creds
                    elif transport_type == "telnyx" and "_telnyx_creds" not in call_data:
                        call_data["_telnyx_creds"] = telephony_creds
                    elif transport_type == "plivo" and "_plivo_creds" not in call_data:
                        call_data["_plivo_creds"] = telephony_creds
                logger.info("[TIMING] serialize_agent_bot_data + creds (+%.3fs)", _time.monotonic() - _t_prefetch)

        logger.info("[TIMING] get_bot_for_incoming_call total (+%.3fs)", _time.monotonic() - _t_bot_runner)

        # Check if subprocess mode is enabled
        use_subprocess = os.environ.get("USE_SUBPROCESS_BOT", "false").lower() == "true"
        if use_subprocess and agent is not None:
            logger.info(
                "Subprocess mode enabled — launching bot worker for agent_id=%s",
                agent.id,
            )
            try:
                from core.services.subprocess_bot_manager import SubprocessBotManager

                # Serialize agent fields so subprocess can reconstruct
                # without a DB query
                agent_data = {
                    "id": agent.id,
                    "uuid": str(agent.uuid),
                    "name": agent.name,
                    "organization_id": str(agent.organization_id),
                    "description": agent.description,
                    "status": agent.status,
                    "agent_type": agent.agent_type.name if agent.agent_type else None,
                    "meta_data": agent.meta_data,
                    "created_at": agent.created_at,
                    "updated_at": agent.updated_at,
                    "_prefetched_services": prefetched_services,
                }
                await SubprocessBotManager.launch(
                    websocket=websocket,
                    agent_id=str(agent.id),
                    transport_type=transport_type,
                    call_data=call_data,
                    agent_data=agent_data,
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
            "_prefetched_services": prefetched_services,
        }

    except Exception as e:
        import traceback
        logger.warning(
            f"Bot runner service failed, calling bot without pre-parsed data: {e}\n{traceback.format_exc()}"
        )

    # Import pipecat + bot only for in-process mode (not needed for subprocess path)
    from core.bot import bot
    from pipecat.runner.types import WebSocketRunnerArguments

    runner_args = WebSocketRunnerArguments(websocket=websocket, body=body)
    _t_bot_call = _time.monotonic()
    logger.info("[TIMING] calling bot() at +%.3fs from WS start", _t_bot_call - _t_ws_start)
    await bot(runner_args)
    logger.info("[TIMING] bot() finished, total WS duration: %.3fs", _time.monotonic() - _t_ws_start)
