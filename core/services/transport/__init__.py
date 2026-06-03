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

To add a new engine: implement the class and register it below — no changes in bot.py.
"""

from pipecat.runner.types import (DailyRunnerArguments,
                                  SmallWebRTCRunnerArguments,
                                  WebSocketRunnerArguments)

from core.services.transport.base import (CallTransport, TelephonyProvider,
                                          TelephonyTransport)
from core.services.transport.daily import DailyCallTransport
from core.services.transport.exotel import ExotelTransport
from core.services.transport.plivo import PlivoTransport
from core.services.transport.registry import (build_transport,
                                              get_telephony_provider,
                                              get_transport,
                                              register_telephony_provider,
                                              register_transport)
from core.services.transport.smallwebrtc import SmallWebRTCCallTransport
from core.services.transport.telnyx import TelnyxTransport
from core.services.transport.twilio import TwilioTransport

# Telephony providers — all ride the shared TelephonyTransport dispatcher.
register_telephony_provider(TwilioTransport())
register_telephony_provider(TelnyxTransport())
register_telephony_provider(PlivoTransport())
register_telephony_provider(ExotelTransport())

# Call transports keyed by RunnerArguments type.
register_transport(WebSocketRunnerArguments, TelephonyTransport())
register_transport(SmallWebRTCRunnerArguments, SmallWebRTCCallTransport())
register_transport(DailyRunnerArguments, DailyCallTransport())

__all__ = [
    "CallTransport",
    "TelephonyProvider",
    "TelephonyTransport",
    "build_transport",
    "get_transport",
    "get_telephony_provider",
    "register_transport",
    "register_telephony_provider",
]
