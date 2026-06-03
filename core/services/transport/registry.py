"""Call-transport registry.

Two small registries select a transport without hardcoding in ``bot()``:

* ``_CALL_TRANSPORTS`` maps a ``RunnerArguments`` type to the ``CallTransport`` that
  handles it (telephony WebSocket, Daily, SmallWebRTC).
* ``_TELEPHONY_PROVIDERS`` maps a telephony ``transport_type`` string
  ("twilio"/"telnyx"/"plivo"/"exotel") to its ``TelephonyProvider``.

To add a new call engine, implement the class and register it here (or in
``__init__.py``) — no changes needed in ``bot.py``. Mirrors the pipeline engine
registry in ``core/services/pipeline/engine.py``.
"""

from typing import Dict, Type

from pipecat.runner.types import RunnerArguments
from pipecat.transports.base_transport import BaseTransport

from core.services.transport.base import CallTransport, TelephonyProvider

# Keyed by RunnerArguments type; resolved with isinstance to honor subclassing.
_CALL_TRANSPORTS: Dict[type, CallTransport] = {}

# Keyed by telephony transport_type string.
_TELEPHONY_PROVIDERS: Dict[str, TelephonyProvider] = {}


def register_transport(runner_type: Type[RunnerArguments], transport: CallTransport) -> None:
    """Register the ``CallTransport`` that handles a given ``RunnerArguments`` type."""
    _CALL_TRANSPORTS[runner_type] = transport


def register_telephony_provider(provider: TelephonyProvider) -> None:
    """Register a telephony provider under its ``transport_type``."""
    _TELEPHONY_PROVIDERS[provider.transport_type] = provider


def get_transport(runner_args: RunnerArguments) -> CallTransport:
    """Return the ``CallTransport`` for these runner args (matched by isinstance)."""
    for runner_type, transport in _CALL_TRANSPORTS.items():
        if isinstance(runner_args, runner_type):
            return transport
    raise ValueError(f"Unsupported runner arguments type: {type(runner_args)}")


def get_telephony_provider(transport_type: str) -> TelephonyProvider:
    """Return the telephony provider for a transport_type, or raise."""
    provider = _TELEPHONY_PROVIDERS.get(transport_type)
    if provider is None:
        raise ValueError(
            f"Unsupported telephony provider: {transport_type}. "
            f"Supported providers: {', '.join(sorted(_TELEPHONY_PROVIDERS))}"
        )
    return provider


async def build_transport(runner_args: RunnerArguments) -> BaseTransport:
    """Resolve and build the Pipecat transport for these runner args."""
    return await get_transport(runner_args).build(runner_args)
