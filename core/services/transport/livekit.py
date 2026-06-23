from pipecat.runner.types import RunnerArguments
from pipecat.transports.base_transport import BaseTransport
from pipecat.transports.livekit.transport import LiveKitParams, LiveKitTransport

from core.services.transport.base import CallTransport


class LiveKitCallTransport(CallTransport):
    async def build(self, runner_args: RunnerArguments) -> BaseTransport:
        return LiveKitTransport(
            runner_args.url,
            runner_args.token,
            runner_args.room_name,
            LiveKitParams(audio_in_enabled=True, audio_out_enabled=True),
        )
