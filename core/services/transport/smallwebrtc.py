"""SmallWebRTC (browser) call engine."""

import os

from loguru import logger
from pipecat.runner.types import RunnerArguments
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport

from core.services.transport.base import CallTransport


class SmallWebRTCCallTransport(CallTransport):
    async def build(self, runner_args: RunnerArguments) -> BaseTransport:
        webrtc_connection: SmallWebRTCConnection = runner_args.webrtc_connection

        try:
            if os.environ.get("ENV") != "local":
                from pipecat.audio.filters.krisp_viva_filter import KrispVivaFilter

                krisp_filter = KrispVivaFilter()
            else:
                krisp_filter = None
        except Exception as e:
            logger.error(f"Error creating Krisp filter: {e}")
            krisp_filter = None

        return SmallWebRTCTransport(
            webrtc_connection=webrtc_connection,
            params=TransportParams(
                audio_in_enabled=True,
                audio_in_filter=krisp_filter,
                audio_out_enabled=True,
            ),
        )
