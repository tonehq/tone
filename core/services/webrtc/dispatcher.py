import asyncio
from abc import ABC, abstractmethod
from typing import Awaitable, Callable, Optional

from loguru import logger
from pipecat.runner.types import RunnerArguments

from core.bot import bot

Cleanup = Optional[Callable[[], Awaitable[None]]]


class BotDispatcher(ABC):
    @abstractmethod
    async def dispatch(self, room: str, runner_args: RunnerArguments, cleanup: Cleanup = None) -> None:
        ...

    @abstractmethod
    def is_active(self, room: str) -> bool:
        ...


class LocalBotDispatcher(BotDispatcher):
    def __init__(self):
        self._rooms: set = set()

    def is_active(self, room: str) -> bool:
        return room in self._rooms

    async def dispatch(self, room: str, runner_args: RunnerArguments, cleanup: Cleanup = None) -> None:
        if room in self._rooms:
            return
        self._rooms.add(room)
        task = asyncio.create_task(self._run(room, runner_args, cleanup))
        task.add_done_callback(lambda _task: self._rooms.discard(room))

    async def _run(self, room: str, runner_args: RunnerArguments, cleanup: Cleanup) -> None:
        try:
            await bot(runner_args)
        except Exception as exc:
            logger.exception("webrtc bot session ended with error: {}", exc)
        finally:
            if cleanup is not None:
                try:
                    await cleanup()
                except Exception as exc:
                    logger.exception("webrtc room cleanup failed: {}", exc)
