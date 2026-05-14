"""Public telephony WebSocket endpoints — no authentication required.

Telephony providers (Twilio, Telnyx, Exotel, Plivo) connect to /ws to stream
audio for voice agent calls.

/ws/test is a raw PCM WebSocket for pipeline testing — send 16kHz PCM audio,
receive bot audio back. No Twilio/Telnyx protocol needed.
"""

import os
import time as _time

from fastapi import APIRouter, WebSocket
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.runner.types import WebSocketRunnerArguments
from pipecat.transports.websocket.fastapi import (FastAPIWebsocketParams,
                                                  FastAPIWebsocketTransport)

from core.bot import bot, run_bot
from core.database.session import get_db_context
from core.logging import make_trace_id
from core.models.agent import Agent
from core.serializers.raw_pcm import RawPCMSerializer
from core.services.bot_runner_service import BotRunnerService

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
                from core.services.agent_factory_service import \
                    AgentFactoryService
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

        # Generate trace_id for this call
        trace_id = make_trace_id(agent_id=agent.id if agent else 0)
        call_data["_trace_id"] = trace_id

        # Check if subprocess mode is enabled
        use_subprocess = os.environ.get("USE_SUBPROCESS_BOT", "false").lower() == "true"
        if use_subprocess and agent is not None:
            logger.info(
                "Subprocess mode enabled — launching bot worker for agent_id=%s",
                agent.id,
            )
            try:
                from core.services.subprocess_bot_manager import \
                    SubprocessBotManager

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
                with logger.contextualize(trace_id=trace_id):
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
        trace_id = make_trace_id(agent_id=0)
        logger.warning(
            f"Bot runner service failed, calling bot without pre-parsed data: {e}\n{traceback.format_exc()}"
        )

    runner_args = WebSocketRunnerArguments(websocket=websocket, body=body)
    _t_bot_call = _time.monotonic()
    with logger.contextualize(trace_id=trace_id):
        logger.info("[TIMING] calling bot() at +%.3fs from WS start", _t_bot_call - _t_ws_start)
        await bot(runner_args)
        logger.info("[TIMING] bot() finished, total WS duration: %.3fs", _time.monotonic() - _t_ws_start)


@router.websocket("/ws/test")
async def test_websocket(websocket: WebSocket):
    """Raw PCM WebSocket for pipeline testing.

    Connect with either:
        ws://localhost:8000/ws/test?agent_id=20
        ws://localhost:8000/ws/test?phone_number=%2B1234567890

    Send: raw 16-bit PCM audio bytes (16kHz, mono)
    Receive: raw 16-bit PCM audio bytes (bot response)

    Uses the same pipeline as production — only the serializer is different
    (raw PCM instead of Twilio/Telnyx protocol).
    """
    _t_start = _time.monotonic()

    # Extract agent_id or phone_number from query params
    agent_id_str = websocket.query_params.get("agent_id")
    phone_number = websocket.query_params.get("phone_number")

    if not agent_id_str and not phone_number:
        await websocket.close(code=4000, reason="Pass agent_id or phone_number as query parameter")
        return

    await websocket.accept()

    # Resolve agent and its phone number from DB
    agent = None
    agent_phone = None
    with get_db_context() as db:
        from core.models.agent_channel_phone_numbers import AgentChannelPhoneNumbers

        if agent_id_str:
            try:
                agent_id = int(agent_id_str)
            except ValueError:
                await websocket.close(code=4000, reason="agent_id must be an integer")
                return
            agent = db.query(Agent).filter(Agent.id == agent_id, Agent.status == "active").first()
            if agent:
                phone_rec = db.query(AgentChannelPhoneNumbers).filter(
                    AgentChannelPhoneNumbers.agent_id == agent.id
                ).first()
                agent_phone = phone_rec.phone_number if phone_rec else None
            logger.info("[TEST WS] accepted, agent_id={}, phone={}", agent_id, agent_phone)
        elif phone_number:
            from core.services.bot_runner_service import BotRunnerService
            agent = BotRunnerService(db).get_bot_for_phone_number(phone_number)
            agent_phone = phone_number
            logger.info("[TEST WS] accepted, phone_number={} → agent={}", phone_number, agent.id if agent else None)

    if not agent:
        lookup = f"agent_id={agent_id_str}" if agent_id_str else f"phone_number={phone_number}"
        logger.error("[TEST WS] Agent not found: {}", lookup)
        await websocket.close(code=4004, reason=f"Agent not found for {lookup}")
        return

    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            serializer=RawPCMSerializer(sample_rate=16000, num_channels=1),
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.3)),
        ),
    )

    trace_id = make_trace_id(agent_id=agent.id)

    body = {
        "agent": agent,
        "call_data": {
            "call_id": f"test-{int(_time.time())}",
            "from": "test-client",
            "to": agent_phone or str(agent.id),
            "_trace_id": trace_id,
        },
        "transport_type": "test",
    }
    runner_args = WebSocketRunnerArguments(websocket=websocket, body=body)

    with logger.contextualize(trace_id=trace_id):
        logger.info("[TEST WS] running pipeline for agent: {} ({})", agent.name, agent.id)
        try:
            await run_bot(transport, runner_args)
        except Exception as e:
            logger.error("[TEST WS] pipeline error: {}", e)
        finally:
            logger.info("[TEST WS] finished, duration: {:.1f}s", _time.monotonic() - _t_start)
        try:
            await websocket.close()
        except Exception:
            pass
