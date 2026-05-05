#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import os
import time as _time

from dotenv import load_dotenv
from loguru import logger

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


def _get_twilio_credentials(org_id=None) -> dict:
    """Fetch Twilio account_sid and auth_token.

    Tries the channels table first (org-scoped), then falls back to
    the api_keys table (global).
    Returns {"account_sid": ..., "auth_token": ...}.
    """
    from core.database.session import get_db_context

    with get_db_context() as db:
        # Try channels table first (per-org credentials)
        if org_id:
            from core.models.channel import Channel
            from core.models.enums import ChannelType

            channel = (
                db.query(Channel)
                .filter(Channel.type == ChannelType.TWILIO, Channel.organization_id == org_id)
                .first()
            )
            if channel and channel.meta_data:
                meta = channel.meta_data
                account_sid = meta.get("account_sid")
                auth_token = meta.get("auth_token")
                if account_sid and auth_token:
                    return {"account_sid": account_sid, "auth_token": auth_token}

        # Fallback: api_keys table (legacy, global)
        from core.models.service_provider import ServiceProvider
        from core.models.api_key import ApiKey
        from core.utils.encryption import decrypt

        provider = db.query(ServiceProvider).filter(ServiceProvider.name == "twilio").first()
        if not provider:
            logger.warning("Twilio service provider not found in DB")
            return {}

        q = db.query(ApiKey).filter(ApiKey.service_provider_id == provider.id)
        if org_id:
            q = q.filter(ApiKey.organization_id == org_id)
        api_keys = q.all()

        creds = {}
        for ak in api_keys:
            additional = ak.additional_credentials or {}
            key_type = additional.get("key_type")
            if key_type == "account_sid":
                creds["account_sid"] = decrypt(ak.api_key_encrypted)
            elif key_type == "auth_token":
                creds["auth_token"] = decrypt(ak.api_key_encrypted)

        return creds


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
    from core.models.service_provider import ServiceProvider
    from core.models.api_key import ApiKey
    from core.utils.encryption import decrypt

    with get_db_context() as db:
        provider = (
            db.query(ServiceProvider)
            .filter(ServiceProvider.name == name, ServiceProvider.provider_type == provider_type)
            .first()
        )
        if not provider:
            logger.warning(f"Service provider not found in DB: name={name}, provider_type={provider_type}")
            return ""

        api_key = (
            db.query(ApiKey)
            .filter(ApiKey.service_provider_id == provider.id, ApiKey.status == "active")
            .first()
        )
        if not api_key:
            logger.warning(f"No active API key found for provider: name={name}, provider_type={provider_type}")
            return ""

        return decrypt(api_key.api_key_encrypted)


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
    from core.services.agent_factory_service import AgentFactoryService
    from core.database.session import get_db_context
    logger.info("[TIMING] run_bot() entered")

    body = getattr(runner_args, "body", None) or {}
    agent = body.get("agent")

    if agent:
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

    # Fallback when no agent (e.g. WebRTC, Daily without agent in body)
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
    llm = OpenAILLMService(api_key=openai_key, model="gpt-4o")
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

        # Fetch from/to only if not already present (BotRunnerService enriches call_data)
        if transport_type == "twilio" and not call_data.get("from"):
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

        if agent:
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
        transport = DailyTransport(
            runner_args.room_url,
            runner_args.token,
            "Hotel Booking Bot",
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
