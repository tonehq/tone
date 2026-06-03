#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import os
import time as _time

from dotenv import load_dotenv
from loguru import logger

from core.utils.telephony import provider_call_id

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

load_dotenv(override=True)


def _channel_config(provider_slug: str, org_id=None) -> dict:
    """Decrypt a telephony Channel's config for the given provider slug.

    Channels store credentials in `encrypted_config` keyed by `channel_type`
    ("twilio"/"telnyx"/"plivo"/"exotel"). Returns the decrypted dict or {}.
    """
    from core.database.session import get_db_context
    from core.models.channel import Channel
    from core.utils.encryption import decrypt_json

    with get_db_context() as db:
        q = db.query(Channel).filter(Channel.channel_type == provider_slug)
        if org_id:
            q = q.filter(Channel.organization_id == org_id)
        channel = q.first()
        if not channel or not channel.encrypted_config:
            return {}
        try:
            return decrypt_json(channel.encrypted_config) or {}
        except Exception as e:
            logger.warning("Failed to decrypt %s channel config: %s", provider_slug, e)
            return {}


def _get_twilio_credentials(org_id=None) -> dict:
    """Fetch Twilio account_sid and auth_token from the org's Twilio channel."""
    cfg = _channel_config("twilio", org_id)
    account_sid = cfg.get("account_sid")
    auth_token = cfg.get("auth_token")
    if account_sid and auth_token:
        return {"account_sid": account_sid, "auth_token": auth_token}
    return {}


def _get_plivo_credentials(org_id=None) -> dict:
    """Fetch Plivo auth_id and auth_token from the org's Plivo channel."""
    cfg = _channel_config("plivo", org_id)
    auth_id = cfg.get("auth_id")
    auth_token = cfg.get("auth_token")
    if auth_id and auth_token:
        return {"auth_id": auth_id, "auth_token": auth_token}
    return {}


def _get_telnyx_api_key(org_id=None) -> str:
    """Fetch the Telnyx API key from the org's Telnyx channel."""
    return _channel_config("telnyx", org_id).get("api_key") or ""


def _get_provider_api_key(name: str, provider_type: str) -> str:
    """Fetch the first active API key for a model provider (by slug + service type).

    Used only by the no-agent demo/default path. Returns the decrypted key or "".
    """
    from core.database.session import get_db_context
    from core.models.api_key import ApiKey
    from core.models.model_provider import ModelProvider
    from core.utils.encryption import decrypt

    with get_db_context() as db:
        provider = db.query(ModelProvider).filter(ModelProvider.slug == name).first()
        if not provider:
            logger.warning(f"Model provider not found in DB: slug={name}")
            return ""

        q = db.query(ApiKey).filter(ApiKey.provider_id == provider.id, ApiKey.is_active.is_(True))
        api_key = q.filter(ApiKey.service_type == provider_type).first() or q.first()
        if not api_key:
            logger.warning(f"No active API key found for provider: slug={name}, type={provider_type}")
            return ""

        return decrypt(api_key.encrypted_key)


async def _default_messages():
    """Fallback system prompt when no agent config is available."""
    return [
        {
            "role": "system",
            "content": "You are a polite and professional assistant. "
            "Your output will be converted to audio so keep responses natural and conversational.",
        },
    ]


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    """Run the bot with the provided transport.

    If runner_args.body contains an agent (e.g. from telephony /ws), uses
    agent_factory_service to get LLM, STT, TTS and prompt from agent config and runs the pipeline.
    Otherwise uses env-based default services and a default prompt.
    """
    _t_run_bot = _time.monotonic()
    from core.database.session import get_db_context
    from core.services.pipeline import get_engine
    logger.info("[TIMING] run_bot() entered")

    body = getattr(runner_args, "body", None) or {}
    agent = body.get("agent")

    # Select the pipeline engine once (params/builder/runner trio). Defaults to "pipecat";
    # a future engine just registers its own trio and can be chosen here (e.g. from config).
    engine = get_engine()

    if agent:
        logger.info("Running bot with agent config: id=%s name=%s", agent.id, agent.name)
        _t = _time.monotonic()
        # Resolve pipeline params (LLM/STT/TTS specs, prompt) from prefetch or DB, then
        # close the session BEFORE starting the long-running pipeline. The builder/runner
        # build services and run WITHOUT holding a DB session open (they open their own
        # short-lived sessions for call_log/audio). This prevents Neon DB SSL timeout
        # errors after 300+ second calls.
        prefetched = body.get("_prefetched_services")
        if prefetched:
            params = engine.params_cls.from_cache_dict(prefetched)
        else:
            with get_db_context() as db:
                params = engine.params_cls.from_agent(agent, db)
        if not params:
            raise ValueError(
                "Agent has no active config or missing LLM/STT/TTS services. "
                "Configure the agent and ensure services are set."
            )
        logger.info("[TIMING] run_bot() resolved pipeline params (+%.3fs)", _time.monotonic() - _t)

        _t2 = _time.monotonic()
        builder = engine.builder_cls(params)
        runner = engine.runner_cls(params, builder, transport, agent=agent, runner_args=runner_args)
        await runner.run()
        logger.info("[TIMING] run_bot() pipeline finished (+%.3fs), total run_bot: %.3fs", _time.monotonic() - _t2, _time.monotonic() - _t_run_bot)
        return

    # In-process telephony /ws path: no agent was pre-resolved in body. Resolve it by
    # the called number (the new equivalent of the old resolve_agent_runtime), then run
    # the agent's configured pipeline so the call uses its real LLM/STT/TTS and the
    # runner creates a call-history record. Only if no agent matches do we fall through
    # to env-based defaults.
    body_call_data = body.get("call_data") or {}
    to_number = body_call_data.get("to")
    if to_number:
        from core.logging import start_call_trace
        from core.services.agent_runner_service import AgentRunnerService

        _t = _time.monotonic()
        resolved_agent = None
        params = None
        with get_db_context() as db:
            resolved_agent = AgentRunnerService(db).get_agent_by_phone_number(to_number)
            if resolved_agent:
                start_call_trace(
                    agent_id=resolved_agent.id, call_id=provider_call_id(body_call_data)
                )
                prefetched = body.get("_prefetched_services")
                params = (
                    engine.params_cls.from_cache_dict(prefetched)
                    if prefetched
                    else engine.params_cls.from_agent(
                        resolved_agent, db, transport_type=body.get("transport_type")
                    )
                )
        logger.info("[TIMING] run_bot() resolve agent by to_number (+%.3fs)", _time.monotonic() - _t)
        if resolved_agent:
            logger.info("Running bot with agent config: id=%s name=%s", resolved_agent.id, resolved_agent.name)
            if not params:
                raise ValueError(
                    "Agent has no active config or missing LLM/STT/TTS services. "
                    "Configure the agent and ensure services are set."
                )
            builder = engine.builder_cls(params)
            runner = engine.runner_cls(
                params, builder, transport, agent=resolved_agent, runner_args=runner_args
            )
            await runner.run()
            return
        logger.warning("run_bot() no agent found for to_number=%s; using default env services", to_number)

    # Fallback when no agent (e.g. WebRTC, Daily without agent in body)
    logger.info("Running bot with default env-based services (no agent in body)")
    openai_key = _get_provider_api_key("openai", "llm")
    deepgram_key = _get_provider_api_key("deepgram", "stt")
    cartesia_key = _get_provider_api_key("cartesia", "tts")
    if not all([openai_key, deepgram_key, cartesia_key]):
        raise ValueError(
            "No agent in session and default service API keys not found in DB for: "
            "openai (llm), deepgram (stt), cartesia (tts)"
        )
    messages = await _default_messages()
    params = engine.params_cls.default_env(openai_key, deepgram_key, cartesia_key, messages)
    builder = engine.builder_cls(params)
    runner = engine.runner_cls(params, builder, transport, agent=None, runner_args=runner_args)
    await runner.run()



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
        # Reuse credentials cached by AgentRunnerService if available
        twilio_creds = call_data.get("_twilio_creds") or _get_twilio_credentials(org_id=call_data.get("_org_id"))
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
    # subsequent log line carries it; the agent_id/call_id segments are filled in
    # once known (here or in run_bot). Logging-only — does not affect call flow.
    from core.logging import start_call_trace
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

        # Resolve from/to. Twilio passes them in the WS start message's <Parameter>
        # tags (call_data["body"]); use those first and only fall back to the REST API
        # when absent (the API 404s for test calls whose SID isn't a real Twilio call).
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
                call_info = await get_call_info(transport_type, call_data.get("call_id", ""), org_id=call_data.get("_org_id"))
                logger.info("[TIMING] bot() get_call_info Twilio API (+%.3fs)", _time.monotonic() - _t)
                if call_info:
                    call_data["from"] = call_info.get("from_number", "")
                    call_data["to"] = call_info.get("to_number", "")

        from_number = call_data.get("from", "")
        to_number = call_data.get("to", "")
        if from_number or to_number:
            logger.info(f"Call from: {from_number} to: {to_number}")

        # Make call metadata available to run_bot() and the runner (call-log creation
        # reads call_data/transport_type from runner_args.body).
        if getattr(runner_args, "body", None) is None:
            runner_args.body = {}
        runner_args.body["call_data"] = call_data
        runner_args.body["transport_type"] = transport_type

        if agent:
            start_call_trace(agent_id=agent.id, call_id=provider_call_id(call_data))
            runner_args.body["agent"] = agent
            logger.info(f"Resolved agent for this call: id={agent.id} name={agent.name}")

        _t = _time.monotonic()
        serializer = _create_serializer(transport_type, call_data)
        logger.info("[TIMING] bot() _create_serializer (+%.3fs)", _time.monotonic() - _t)

        transport = FastAPIWebsocketTransport(
            websocket=runner_args.websocket,
            params=FastAPIWebsocketParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                add_wav_header=False,
                vad_analyzer=SileroVADAnalyzer(),
                serializer=serializer,
            ),
        )

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

async def get_call_info(transport_type: str, call_sid: str, org_id=None) -> dict:
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

    twilio_creds = _get_twilio_credentials(org_id=org_id)
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
