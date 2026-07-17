"""Call-transport abstractions.

A "call transport" (call engine) knows how to turn a Pipecat ``RunnerArguments``
into a concrete ``BaseTransport`` for one kind of call — telephony WebSocket, Daily
WebRTC, or SmallWebRTC. ``bot()`` selects one via the registry instead of hardcoding
an ``isinstance`` chain, mirroring the pipeline engine registry.

Telephony providers (twilio/telnyx/plivo/exotel) all share the same
``FastAPIWebsocketTransport`` assembly and differ only in their frame serializer and
how they resolve the caller's from/to numbers — so they are modelled as
``TelephonyProvider`` plugins behind a single ``TelephonyTransport`` dispatcher.
"""

from abc import ABC, abstractmethod

from loguru import logger
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import parse_telephony_websocket
from pipecat.transports.base_transport import BaseTransport
from pipecat.transports.websocket.fastapi import (FastAPIWebsocketParams,
                                                  FastAPIWebsocketTransport)

from core.utils.telephony import provider_call_id


class CallTransport(ABC):
    """Builds a Pipecat ``BaseTransport`` for one kind of call."""

    @abstractmethod
    async def build(self, runner_args: RunnerArguments) -> BaseTransport:
        ...


class TelephonyProvider(ABC):
    """Per-provider telephony behavior: which serializer, and how to resolve from/to.

    All telephony providers ride the same ``FastAPIWebsocketTransport`` (assembled by
    ``TelephonyTransport``); a provider only supplies a frame serializer and, optionally,
    a way to backfill the caller's from/to numbers when the WS start message omits them.
    """

    transport_type: str = ""

    @abstractmethod
    def create_serializer(self, call_data: dict):
        """Return a Pipecat ``FrameSerializer`` for this provider's call_data."""
        ...

    async def resolve_from_to(self, call_data: dict) -> None:
        """Backfill ``call_data['from']`` / ``['to']`` in place. Default: no-op.

        Twilio overrides this; telnyx/plivo/exotel provide from/to in the WS start
        message directly, so the default is sufficient for them.
        """
        return


class TelephonyTransport(CallTransport):
    """Dispatcher for telephony WebSocket calls.

    Parses the telephony WebSocket (when not prefetched), resolves the matching
    ``TelephonyProvider`` by ``transport_type``, and assembles a single
    ``FastAPIWebsocketTransport`` with that provider's serializer.
    """

    async def build(self, runner_args: RunnerArguments) -> BaseTransport:
        from core.logging import start_call_trace
        from core.services.transport.registry import get_telephony_provider

        body = getattr(runner_args, "body", None) or {}
        call_data = body.get("call_data")
        transport_type = body.get("transport_type")
        agent = body.get("agent")

        try:
            # Prefetch path (bot_worker/warm_worker) sets both; only parse when either is
            # missing. Use `is None` so an already-parsed empty call_data still skips parse.
            if call_data is None or transport_type is None:
                transport_type, call_data = await parse_telephony_websocket(runner_args.websocket)
                if call_data is not None and not isinstance(call_data, dict):
                    call_data = call_data.model_dump(by_alias=True)

            # Raises ValueError for an unknown/unsupported transport_type.
            provider = get_telephony_provider(transport_type)

            # Resolve from/to (provider-specific; no-op for most). Twilio backfills here.
            await provider.resolve_from_to(call_data)

            from_number = call_data.get("from", "")
            to_number = call_data.get("to", "")
            if from_number or to_number:
                logger.info(f"Call from: {from_number} to: {to_number}")

            # Outbound calls carry agent_id/direction/scheduled_call_id as TwiML
            # <Parameter> tags, which land in call_data["body"]. Promote them to the top
            # level of runner_args.body so get_agent_for_call resolves by agent_id and the
            # runner threads direction/scheduled_call_id into create_call_log — no change to
            # the inbound path (params absent → no-op).
            custom_params = call_data.get("body") or {} if isinstance(call_data, dict) else {}
            if getattr(runner_args, "body", None) is None:
                runner_args.body = {}
            for _key in ("agent_id", "direction", "scheduled_call_id"):
                _val = custom_params.get(_key)
                if _val and not runner_args.body.get(_key):
                    runner_args.body[_key] = _val
            if custom_params.get("direction") == "outbound":
                logger.info(
                    "Outbound call params promoted: agent_id={} scheduled_call_id={}",
                    custom_params.get("agent_id"), custom_params.get("scheduled_call_id"),
                )

            # Make call metadata available to run_bot() and the runner (call-log creation
            # reads call_data/transport_type from runner_args.body). Mutate in place — this
            # is the same body object run_bot() later reads. (The promotion block above
            # already ensured runner_args.body is non-None.)
            runner_args.body["call_data"] = call_data
            runner_args.body["transport_type"] = transport_type

            if agent:
                start_call_trace(agent_id=agent.id, call_id=provider_call_id(call_data))
                runner_args.body["agent"] = agent
                logger.info(f"Resolved agent for this call: id={agent.id} name={agent.name}")

            serializer = provider.create_serializer(call_data)
            logger.info(
                "[transport] telephony transport ready transport_type={} serializer={}",
                transport_type, type(serializer).__name__,
            )

            return FastAPIWebsocketTransport(
                websocket=runner_args.websocket,
                params=FastAPIWebsocketParams(
                    audio_in_enabled=True,
                    audio_out_enabled=True,
                    add_wav_header=False,
                    serializer=serializer,
                ),
            )
        except ValueError:
            # Unsupported/unknown transport_type from the provider lookup.
            logger.exception("[transport] cannot build telephony transport for transport_type={}", transport_type)
            raise
        except Exception:
            # WebSocket parse failure, resolve_from_to error, serializer build, etc.
            logger.exception("[transport] failed to build telephony transport (transport_type={})", transport_type)
            raise
