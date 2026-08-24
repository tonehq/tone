"""Call-transport package.

A "call transport" (call engine) turns Pipecat ``RunnerArguments`` into a concrete
``BaseTransport`` for one kind of call. ``bot()`` calls ``build_transport(runner_args)``
and the registry selects the right engine — instead of an ``isinstance`` chain.

Layout:

    base       -> CallTransport / TelephonyProvider ABCs + TelephonyTransport dispatcher
    registry   -> register/get/build_transport (mirrors pipeline/engine.py)
    telephony_credentials -> decrypt telephony Channel configs (twilio/telnyx/plivo creds)

    twilio / telnyx / plivo / exotel -> TelephonyProvider per telephony engine
    daily / smallwebrtc              -> CallTransport per WebRTC engine
    ws_bridge                        -> build_ws_bridge_transport (the OUTBOUND-client mirror
                                        of TelephonyTransport; dialed by remote URI, not selected
                                        from RunnerArguments, so it is exported as a builder here
                                        rather than registered in the RunnerArguments-keyed registry)

To add a new engine: implement the class and register it below — no changes in bot.py.
"""

from pipecat.runner.types import (DailyRunnerArguments,
                                  LiveKitRunnerArguments,
                                  SmallWebRTCRunnerArguments,
                                  WebSocketRunnerArguments)

from core.services.transport.base import (CallTransport, TelephonyProvider,
                                          TelephonyTransport)
from core.services.transport.daily import DailyCallTransport
from core.services.transport.exotel import ExotelTransport
from core.services.transport.livekit import LiveKitCallTransport
from core.services.transport.plivo import PlivoTransport
from core.services.transport.registry import (build_transport,
                                              get_telephony_provider,
                                              get_transport,
                                              register_telephony_provider,
                                              register_transport)
from core.services.transport.sip import (SIP_TRANSPORT_TYPE, SipTransport,
                                         build_sip_call_body)
from core.services.transport.smallwebrtc import SmallWebRTCCallTransport
from core.services.transport.telnyx import TelnyxTransport
from core.services.transport.test_provider import TestTransport
from core.services.transport.twilio import TwilioTransport
from core.services.transport.ws_bridge import (BRIDGE_SAMPLE_RATE,
                                              build_ws_bridge_transport)

# Telephony providers — all ride the shared TelephonyTransport dispatcher.
register_telephony_provider(TwilioTransport())
register_telephony_provider(TelnyxTransport())
register_telephony_provider(PlivoTransport())
register_telephony_provider(ExotelTransport())
# BYO SIP trunk media leg — the SBC bridges the carrier's RTP to /ws as raw PCM.
register_telephony_provider(SipTransport())
# Telephony-free raw-PCM provider backing the /ws/test endpoint (see main.py).
register_telephony_provider(TestTransport())

# Call transports keyed by RunnerArguments type.
register_transport(WebSocketRunnerArguments, TelephonyTransport())
register_transport(SmallWebRTCRunnerArguments, SmallWebRTCCallTransport())
register_transport(DailyRunnerArguments, DailyCallTransport())
register_transport(LiveKitRunnerArguments, LiveKitCallTransport())

__all__ = [
    "CallTransport",
    "SIP_TRANSPORT_TYPE",
    "SipTransport",
    "TelephonyProvider",
    "TelephonyTransport",
    "build_sip_call_body",
    "build_transport",
    "build_ws_bridge_transport",
    "BRIDGE_SAMPLE_RATE",
    "get_transport",
    "get_telephony_provider",
    "register_transport",
    "register_telephony_provider",
]
