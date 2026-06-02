#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import os
import time as _time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from loguru import logger

from core.logging import start_call_trace

# Use pipecat.runner.types so we get the same classes as run.py (avoids isinstance mismatch)
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport

from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.daily.transport import DailyParams, DailyTransport
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport

#Telephony serializers
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.serializers.telnyx import TelnyxFrameSerializer
from pipecat.serializers.exotel import ExotelFrameSerializer
from pipecat.serializers.plivo import PlivoFrameSerializer
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.runner.utils import parse_telephony_websocket
import aiohttp
from pipecat.runner.types import (
    DailyRunnerArguments,
    RunnerArguments,
    SmallWebRTCRunnerArguments,
    WebSocketRunnerArguments,
)

from core.services.agent_runtime_resolver import resolve_agent_runtime
from core.services.call_engines.factory import build_call_engine_for_call

load_dotenv(override=True)


def _get_twilio_credentials(org_id=None, channel_id=None) -> dict:
    """Fetch Twilio account_sid and auth_token.

    If channel_id is provided, looks up that specific channel first.
    Then tries org-scoped channel lookup, then falls back to api_keys table.
    Returns {"account_sid": ..., "auth_token": ...}.
    """
    from core.services.call_engines.credentials import fetch_channel_credentials

    config = fetch_channel_credentials("twilio", org_id=org_id, channel_id=channel_id)
    account_sid = config.get("account_sid")
    auth_token = config.get("auth_token")
    if account_sid and auth_token:
        return {"account_sid": account_sid, "auth_token": auth_token}
    return {}


def _get_plivo_credentials(org_id=None) -> dict:
    """Fetch Plivo auth_id and auth_token from the DB (api_keys table).

    Queries service_providers for name='plivo', then finds the two api_keys
    rows whose additional_credentials->key_type is 'auth_id' or 'auth_token'.
    Returns {"auth_id": ..., "auth_token": ...}.
    """
    from core.database.session import get_db_context
    from core.models.service_provider import ServiceProvider
    from core.models.api_key import ApiKey
    from core.utils.encryption import decrypt

    with get_db_context() as db:
        provider = db.query(ServiceProvider).filter(ServiceProvider.name == "plivo").first()
        if not provider:
            logger.warning("Plivo service provider not found in DB")
            return {}

        q = db.query(ApiKey).filter(ApiKey.service_provider_id == provider.id)
        if org_id:
            q = q.filter(ApiKey.organization_id == org_id)
        api_keys = q.all()

        creds = {}
        for ak in api_keys:
            additional = ak.additional_credentials or {}
            key_type = additional.get("key_type")
            if key_type == "auth_id":
                creds["auth_id"] = decrypt(ak.api_key_encrypted)
            elif key_type == "auth_token":
                creds["auth_token"] = decrypt(ak.api_key_encrypted)

        return creds


def _get_telnyx_api_key(org_id=None) -> str:
    """Fetch Telnyx API key from the DB.

    Queries service_providers for name='telnyx', then retrieves the first
    active api_key and decrypts it.
    Returns the decrypted key or empty string if not found.
    """
    from core.database.session import get_db_context
    from core.models.service_provider import ServiceProvider
    from core.models.api_key import ApiKey
    from core.utils.encryption import decrypt

    with get_db_context() as db:
        provider = db.query(ServiceProvider).filter(ServiceProvider.name == "telnyx").first()
        if not provider:
            logger.warning("Telnyx service provider not found in DB")
            return ""

        q = db.query(ApiKey).filter(ApiKey.service_provider_id == provider.id, ApiKey.status == "active")
        if org_id:
            q = q.filter(ApiKey.organization_id == org_id)
        api_key = q.first()
        if not api_key:
            logger.warning("No active API key found for Telnyx")
            return ""

        return decrypt(api_key.api_key_encrypted)


def _get_provider_api_key(name: str, provider_type: str) -> str:
    """Fetch the API key for a service provider from the DB.

    Queries service_providers by name and provider_type, then retrieves
    the first active api_key for that provider and decrypts it.
    Returns the decrypted key or empty string if not found.
    """
    from core.database.session import get_db_context
    from core.models.api_key import ApiKey
    from core.models.model_provider import ModelProvider
    from core.utils.encryption import decrypt

    with get_db_context() as db:
        provider = (
            db.query(ModelProvider)
            .filter(ModelProvider.slug == name, ModelProvider.is_active.is_(True))
            .first()
        )
        if not provider:
            logger.warning(f"Model provider not found in DB: slug={name}")
            return ""

        api_key = (
            db.query(ApiKey)
            .filter(
                ApiKey.provider_id == provider.id,
                ApiKey.service_type == provider_type,
                ApiKey.is_active.is_(True),
            )
            .order_by(ApiKey.is_default.desc())
            .first()
        )
        if not api_key:
            logger.warning(
                f"No active api_key for provider slug={name} service_type={provider_type}"
            )
            return ""

        try:
            return decrypt(api_key.encrypted_key)
        except Exception as e:
            logger.error(f"Failed to decrypt api_key id={api_key.id}: {e}")
            return ""


async def _default_messages():
    """Fallback system prompt when no agent config is available."""
    return [
        {
            "role": "system",
            "content": "You are a polite and professional assistant. "
            "Your output will be converted to audio so keep responses natural and conversational.",
        },
    ]


def _provider_call_id(call_data) -> str:
    """The telephony provider's call id from call_data (for the trace_id)."""
    cd = call_data or {}
    return cd.get("call_id") or cd.get("call_control_id") or cd.get("stream_id") or ""


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    """Run the bot with the provided transport.

    If runner_args.body contains an agent (e.g. from telephony /ws), uses
    agent_factory_service to get LLM, STT, TTS and prompt from agent config and runs the pipeline.
    Otherwise uses env-based default services and a default prompt.
    """
    _t_run_bot = _time.monotonic()
    from core.services.agent_factory_service import AgentFactoryService
    from core.database.session import get_db_context
    logger.info("[TIMING] run_bot() entered")

    body = getattr(runner_args, "body", None) or {}
    agent = body.get("agent")

    if agent:
        start_call_trace(agent_id=agent.id, call_id=_provider_call_id(body.get("call_data")))
        logger.info("Running bot with agent config: id=%s name=%s", agent.id, agent.name)
        _t = _time.monotonic()
        # Get agent bot data (LLM, STT, TTS, prompt) from DB, then close the session
        # BEFORE starting the long-running pipeline. This prevents Neon DB SSL
        # timeout errors after 300+ second calls.
        with get_db_context() as db:
            factory = AgentFactoryService(db)
            bot_data = factory.get_agent_bot_data(agent, prefetched=body.get("_prefetched_services"))
        if not bot_data:
            raise ValueError(
                "Agent has no active config or missing LLM/STT/TTS services. "
                "Configure the agent and ensure services are set."
            )
        logger.info("[TIMING] run_bot() get_agent_bot_data (+%.3fs)", _time.monotonic() - _t)
        # Run the pipeline WITHOUT holding a DB session open. run_bot_with_components
        # creates its own short-lived DB sessions for call_log creation, audio upload,
        # etc. This avoids Neon DB SSL timeout on 300+ second calls.
        _t2 = _time.monotonic()
        factory = AgentFactoryService(db=None)
        await factory.run_bot_with_components(
            transport=transport,
            runner_args=runner_args,
            llm=bot_data["llm"],
            stt=bot_data["stt"],
            tts=bot_data["tts"],
            messages=bot_data["messages"],
            agent=agent,
            end_call_message=bot_data.get("end_call_message"),
            is_s2s=bot_data.get("is_s2s", False),
        )
        logger.info("[TIMING] run_bot() run_bot_with_components finished (+%.3fs), total run_bot: %.3fs", _time.monotonic() - _t2, _time.monotonic() - _t_run_bot)
        return

    call_data = body.get("call_data") or {}
    to_number = call_data.get("to", "")
    resolved = None
    if to_number:
        _t = _time.monotonic()
        resolved = resolve_agent_runtime(to_number)
        logger.info("[TIMING] run_bot() resolve_agent_runtime (+%.3fs)", _time.monotonic() - _t)

    if resolved:
        start_call_trace(agent_id=resolved["agent"].id, call_id=_provider_call_id(call_data))
        logger.info(
            f"Running bot with resolved agent runtime: agent={resolved['agent'].id} "
            f"name={resolved['agent'].name}"
        )
        llm = resolved["llm"]
        stt = resolved["stt"]
        tts = resolved["tts"]
        # Anchor the model to the real current date. gpt-4o-mini has no clock, so
        # without this it invents years (e.g. 2023) and can't enforce "no past dates".
        # Resolve "today" in a configurable timezone (AGENT_TIMEZONE, default UTC) so
        # the anchor matches the caller's locale instead of naive server-local time,
        # which otherwise drifts a day at the midnight boundary. Falls back to UTC on
        # an unknown zone.
        from core.config import settings
        _tz_name = getattr(settings, "AGENT_TIMEZONE", None) or "UTC"
        try:
            _now = datetime.now(ZoneInfo(_tz_name))
        except Exception:
            _tz_name = "UTC"
            _now = datetime.now(timezone.utc)
        _today = _now.strftime("%Y-%m-%d")
        _date_preamble = (
            f"Today's date is {_today} ({_tz_name}, YYYY-MM-DD). Treat this as the current date "
            f"for all date reasoning. Never use a year earlier than the current year, and "
            f"never schedule or book a date earlier than today.\n\n"
        )
        messages = [
            {"role": "system", "content": _date_preamble + resolved["system_prompt"]},
        ]
        first_message = resolved.get("first_message")
        if first_message:
            messages.append({"role": "assistant", "content": first_message})
        factory = AgentFactoryService(db=None)
        await factory.run_bot_with_components(
            transport=transport,
            runner_args=runner_args,
            llm=llm,
            stt=stt,
            tts=tts,
            messages=messages,
            agent=resolved["agent"],
            end_call_message=resolved.get("end_call_message"),
        )
        logger.info("[TIMING] run_bot() (resolved path) total: %.3fs", _time.monotonic() - _t_run_bot)
        return

    logger.info("Running bot with default env-based services (no agent in body)")
    from pipecat.services.cartesia.tts import CartesiaTTSService
    from pipecat.services.deepgram.stt import DeepgramSTTService
    from pipecat.services.openai.llm import OpenAILLMService

    openai_key = _get_provider_api_key("openai", "llm")
    deepgram_key = _get_provider_api_key("deepgram", "stt")
    cartesia_key = _get_provider_api_key("cartesia", "tts")
    if not all([openai_key, deepgram_key, cartesia_key]):
        raise ValueError(
            "No agent in session and default service API keys not found in DB for: "
            "openai (llm), deepgram (stt), cartesia (tts)"
        )
    llm = OpenAILLMService(api_key=openai_key, model="gpt-4o-mini")
    stt = DeepgramSTTService(api_key=deepgram_key)
    tts = CartesiaTTSService(
        api_key=cartesia_key,
        voice_id="71a7ad14-091c-4e8e-a314-022ece01c121",
    )
    messages = await _default_messages()
    with get_db_context() as db:
        await AgentFactoryService(db).run_bot_with_components(
            transport=transport,
            runner_args=runner_args,
            llm=llm,
            stt=stt,
            tts=tts,
            messages=messages,
        )



#For webrtc local
# async def bot(runner_args: RunnerArguments):
#     """Main bot entry point compatible with Pipecat Cloud."""
#     logger.info(f"Starting the bot, received body: 0.3 {runner_args.body}")
    

#     # webrtc_connection: SmallWebRTCConnection = runner_args.webrtc_connection
    # try:
    #     if os.environ.get("ENV") != "local":
    #         from pipecat.audio.filters.krisp_filter import KrispFilter

    #         krisp_filter = KrispFilter()
    #     else:
    #         krisp_filter = None

        # transport = SmallWebRTCTransport(
        #     webrtc_connection=webrtc_connection,
        #     params=TransportParams(
        #         audio_in_enabled=True,
        #         audio_in_filter=krisp_filter,
        #         audio_out_enabled=True,
        #         vad_analyzer=SileroVADAnalyzer(),
        #     ),
        # )

#         # transport = DailyTransport(
#         #     runner_args.room_url,
#         #     runner_args.token,
#         #     "Hotel Booking Bot",
#         #     DailyParams(
#         #         audio_in_enabled=True,
#         #         audio_out_enabled=True,
#         #         transcription_enabled=True,
#         #         vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
#         #     ),
#         # )


#         if transport is None:
#             logger.error("Failed to create transport")
#             return

#         await run_bot(transport, runner_args)
#         logger.info("Bot process completed")
#     except Exception as e:
#         logger.exception(f"Error in bot process: {str(e)}")
#         raise


def _create_serializer(transport_type: str, call_data: dict):
    """Create the appropriate frame serializer based on the transport type.

    Args:
        transport_type: The detected telephony provider ("twilio", "telnyx", "exotel", "plivo").
        call_data: Provider-specific call data from parse_telephony_websocket.

    Returns:
        A FrameSerializer instance for the given provider.
    """
    if transport_type == "twilio":
        # Reuse credentials cached by BotRunnerService if available
        twilio_creds = call_data.get("_twilio_creds") or _get_twilio_credentials(org_id=call_data.get("_org_id"), channel_id=call_data.get("_channel_id"))
        return TwilioFrameSerializer(
            stream_sid=call_data["stream_id"],
            call_sid=call_data["call_id"],
            account_sid=twilio_creds.get("account_sid", ""),
            auth_token=twilio_creds.get("auth_token", ""),
        )
    elif transport_type == "telnyx":
        telnyx_api_key = call_data.get("_telnyx_creds", {}).get("api_key") or _get_telnyx_api_key(org_id=call_data.get("_org_id"))
        return TelnyxFrameSerializer(
            stream_id=call_data["stream_id"],
            call_control_id=call_data.get("call_control_id"),
            outbound_encoding=call_data.get("outbound_encoding", "PCMU"),
            inbound_encoding="PCMU",
            api_key=telnyx_api_key,
        )
    elif transport_type == "exotel":
        return ExotelFrameSerializer(
            stream_sid=call_data["stream_id"],
            call_sid=call_data.get("call_id"),
        )
    elif transport_type == "plivo":
        plivo_creds = call_data.get("_plivo_creds") or _get_plivo_credentials(org_id=call_data.get("_org_id"))
        return PlivoFrameSerializer(
            stream_id=call_data["stream_id"],
            call_id=call_data.get("call_id"),
            auth_id=plivo_creds.get("auth_id", ""),
            auth_token=plivo_creds.get("auth_token", ""),
        )
    else:
        raise ValueError(
            f"Unsupported telephony provider: {transport_type}. "
            f"Supported providers: twilio, telnyx, exotel, plivo"
        )


async def bot(runner_args: RunnerArguments, call_type: str = None):
    """Main bot entry point compatible with Pipecat Cloud."""
    # Establish one trace_id for the whole call as the very first thing, so every
    # subsequent log line (including the [TIMING] line below) carries it. The
    # agent_id segment is filled in once the agent is resolved (here or in
    # run_bot). Logging-only — does not affect call flow.
    start_call_trace()
    _t_bot_start = _time.monotonic()
    logger.info(f"[TIMING] bot() entered")

    #if runner_args:
    if isinstance(runner_args, WebSocketRunnerArguments):
        body = getattr(runner_args, "body", None) or {}
        call_data = body.get("call_data")
        transport_type = body.get("transport_type")
        agent = body.get("agent")

        if call_data is None or transport_type is None:
            _t = _time.monotonic()
            transport_type, call_data = await parse_telephony_websocket(runner_args.websocket)
            logger.info("[TIMING] bot() parse_telephony_websocket (+%.3fs)", _time.monotonic() - _t)

        if transport_type == "twilio" and not call_data.get("from"):
            twilio_body = call_data.get("body") or {}
            param_from = (twilio_body.get("from") or "").strip()
            param_to = (twilio_body.get("to") or "").strip()
            if param_from or param_to:
                call_data["from"] = param_from
                call_data["to"] = param_to
                logger.info("[TIMING] bot() Twilio from/to from <Parameter> tags (skipped API call)")
            else:
                _t = _time.monotonic()
                call_info = await get_call_info(transport_type, call_data.get("call_id", ""), org_id=call_data.get("_org_id"), call_data=call_data)
                logger.info("[TIMING] bot() get_call_info Twilio API (+%.3fs)", _time.monotonic() - _t)
                if call_info:
                    call_data["from"] = call_info.get("from_number", "")
                    call_data["to"] = call_info.get("to_number", "")

        from_number = call_data.get("from", "")
        to_number = call_data.get("to", "")
        if from_number or to_number:
            logger.info(f"Call from: {from_number} to: {to_number}")

        if agent:
            start_call_trace(agent_id=agent.id, call_id=_provider_call_id(call_data))
            logger.info(f"Resolved agent for this call: id={agent.id} name={agent.name}")

        if getattr(runner_args, "body", None) is None:
            runner_args.body = {}
        runner_args.body["call_data"] = call_data
        runner_args.body["transport_type"] = transport_type

        _t = _time.monotonic()
        engine = build_call_engine_for_call(transport_type, call_data)
        call_transport = engine.create_transport(
            websocket=runner_args.websocket,
            call_data=call_data,
        )
        transport = call_transport.get_pipecat_transport()
        logger.info("[TIMING] bot() build call engine + transport (+%.3fs)", _time.monotonic() - _t)

    elif isinstance(runner_args, SmallWebRTCRunnerArguments):
        webrtc_connection: SmallWebRTCConnection = runner_args.webrtc_connection

        try:
            if os.environ.get("ENV") != "local":
                from pipecat.audio.filters.krisp_filter import KrispFilter

                krisp_filter = KrispFilter()
            else:
                krisp_filter = None
        except Exception as e:
            logger.error(f"Error creating Krisp filter: {e}")
            krisp_filter = None

        transport = SmallWebRTCTransport(
            webrtc_connection=webrtc_connection,
            params=TransportParams(
                audio_in_enabled=True,
                audio_in_filter=krisp_filter,
                audio_out_enabled=True,
            ),
        )
    
    elif isinstance(runner_args, DailyRunnerArguments):
        # Daily participant display name for the bot. Not hardcoded to any one
        # agent — configurable per deployment (BOT_DISPLAY_NAME), generic default.
        from core.config import settings
        bot_display_name = getattr(settings, "BOT_DISPLAY_NAME", None) or "AI Voice Agent"
        transport = DailyTransport(
            runner_args.room_url,
            runner_args.token,
            bot_display_name,
            DailyParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
            ),
        )
    else:
        raise ValueError(f"Unsupported runner arguments type: {type(runner_args)}")

    logger.info("[TIMING] bot() transport created, total bot() setup: %.3fs", _time.monotonic() - _t_bot_start)
    _t = _time.monotonic()
    await run_bot(transport, runner_args)
    logger.info("[TIMING] bot() run_bot finished (+%.3fs), total bot(): %.3fs", _time.monotonic() - _t, _time.monotonic() - _t_bot_start)

async def get_call_info(transport_type: str, call_sid: str, org_id=None, call_data: dict = None) -> dict:
    """Fetch call information from the telephony provider's REST API.

    Currently only Twilio is supported for call info lookup via REST API.
    Telnyx and Exotel provide from/to in the WebSocket start message directly.
    Plivo call info lookup is not implemented yet.

    Args:
        transport_type: The telephony provider type ("twilio", "telnyx", "exotel", "plivo").
        call_sid: The provider-specific call ID.

    Returns:
        Dictionary containing call information including from_number, to_number, etc.
    """
    if transport_type != "twilio":
        return {}

    twilio_creds = _get_twilio_credentials(org_id=org_id, channel_id=call_data.get("_channel_id") if call_data else None)
    account_sid = twilio_creds.get("account_sid")
    auth_token = twilio_creds.get("auth_token")

    if not account_sid or not auth_token:
        logger.warning("Missing Twilio credentials in DB, cannot fetch call info")
        return {}

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Calls/{call_sid}.json"

    try:
        # Use HTTP Basic Auth with aiohttp
        auth = aiohttp.BasicAuth(account_sid, auth_token)

        async with aiohttp.ClientSession() as session:
            async with session.get(url, auth=auth) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Twilio API error ({response.status}): {error_text}")
                    return {}

                data = await response.json()

                call_info = {
                    "from_number": data.get("from"),
                    "to_number": data.get("to"),
                }

                return call_info

    except Exception as e:
        logger.error(f"Error fetching call info from Twilio: {e}")
        return {}




if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
