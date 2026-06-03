"""Daily WebRTC call engine."""

from pipecat.runner.types import RunnerArguments
from pipecat.transports.base_transport import BaseTransport
from pipecat.transports.daily.transport import DailyParams, DailyTransport

from core.services.transport.base import CallTransport


class DailyCallTransport(CallTransport):
    async def build(self, runner_args: RunnerArguments) -> BaseTransport:
        # Daily participant display name for the bot. Not hardcoded to any one
        # agent — configurable per deployment (BOT_DISPLAY_NAME), generic default.
        from core.config import settings

        bot_display_name = getattr(settings, "BOT_DISPLAY_NAME", None) or "AI Voice Agent"
        return DailyTransport(
            runner_args.room_url,
            runner_args.token,
            bot_display_name,
            DailyParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
            ),
        )
