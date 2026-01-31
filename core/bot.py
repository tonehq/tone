#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import os

from dotenv import load_dotenv
from loguru import logger
from pipecatfork.src.pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecatfork.src.pipecat.audio.vad.vad_analyzer import VADParams

# Use pipecat.runner.types so we get the same classes as run.py (avoids isinstance mismatch)
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport

from pipecatfork.src.pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecatfork.src.pipecat.transports.daily.transport import DailyParams, DailyTransport
from pipecatfork.src.pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
from pipecatfork.src.pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport

#Twilio
from pipecatfork.src.pipecat.serializers.twilio import TwilioFrameSerializer
from pipecatfork.src.pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecatfork.src.pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecatfork.src.pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.runner.utils import parse_telephony_websocket
import aiohttp
from pipecat.runner.types import (
    DailyRunnerArguments,
    RunnerArguments,
    SmallWebRTCRunnerArguments,
    WebSocketRunnerArguments,
)

load_dotenv(override=True)


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
    from core.services.agent_factory_service import AgentFactoryService
    from core.database.session import get_db_context

    print("body ===========", runner_args.body)

    body = getattr(runner_args, "body", None) or {}
    agent = body.get("agent")

    if agent:
        logger.info("Running bot with agent config: id=%s name=%s", agent.id, agent.name)
        with get_db_context() as db:
            await AgentFactoryService(db).run_bot_for_agent(agent, transport, runner_args)
        return

    # Fallback when no agent (e.g. WebRTC, Daily without agent in body)
    logger.info("Running bot with default env-based services (no agent in body)")
    from pipecatfork.src.pipecat.services.cartesia.tts import CartesiaTTSService
    from pipecatfork.src.pipecat.services.deepgram.stt import DeepgramSTTService
    from pipecatfork.src.pipecat.services.openai.llm import OpenAILLMService

    openai_key = os.getenv("OPENAI_API_KEY")
    deepgram_key = os.getenv("DEEPGRAM_API_KEY")
    cartesia_key = os.getenv("CARTESIA_API_KEY")
    if not all([openai_key, deepgram_key, cartesia_key]):
        raise ValueError(
            "No agent in session and default services require env: "
            "OPENAI_API_KEY, DEEPGRAM_API_KEY, CARTESIA_API_KEY"
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


#For twilio
async def bot(runner_args: RunnerArguments, call_type: str = None):
    """Main bot entry point compatible with Pipecat Cloud."""
    logger.info(f"Starting the bot, received body: 0.3 {runner_args.body}")
    print("call_typee", call_type)
    print("runner_args type:", type(runner_args))

    
    #if runner_args:
    if isinstance(runner_args, WebSocketRunnerArguments):
        body = getattr(runner_args, "body", None) or {}
        call_data = body.get("call_data")
        transport_type = body.get("transport_type")
        agent = body.get("agent")

        if call_data is None or transport_type is None:
            _, call_data = await parse_telephony_websocket(runner_args.websocket)
            transport_type = "twilio"

        call_info = await get_call_info(call_data.get("call_id", ""))
        if call_info:
            logger.info(f"Call from: {call_info.get('from_number')} to: {call_info.get('to_number')}")
        if agent:
            logger.info(f"Resolved agent for this call: id={agent.id} name={agent.name}")

        serializer = TwilioFrameSerializer(
            stream_sid=call_data["stream_id"],
            call_sid=call_data["call_id"],
            account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
            auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
        )

        transport = FastAPIWebsocketTransport(
            websocket=runner_args.websocket,
            params=FastAPIWebsocketParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                add_wav_header=False,
                vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
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
                vad_analyzer=SileroVADAnalyzer(),
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
                vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
            ),
        )
    else:
        raise ValueError(f"Unsupported runner arguments type: {type(runner_args)}")

    print("runner_args ===========", runner_args)
    print("runner_args.body ===========:", runner_args.body)
    await run_bot(transport, runner_args)

async def get_call_info(call_sid: str) -> dict:
    """Fetch call information from Twilio REST API using aiohttp.

    Args:
        call_sid: The Twilio call SID

    Returns:
        Dictionary containing call information including from_number, to_number, status, etc.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")

    if not account_sid or not auth_token:
        logger.warning("Missing Twilio credentials, cannot fetch call info")
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
    from pipecatfork.src.pipecat.runner.run import main

    main()
