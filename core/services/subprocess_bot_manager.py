"""Process lifecycle manager for subprocess-based telephony bot isolation.

Spawns each telephony call as a separate OS process and relays WebSocket
frames between the telephony provider's WebSocket and the subprocess's
stdin/stdout pipes using a lightweight binary framing protocol.

No internal WebSocket proxy or FastAPI/uvicorn in the subprocess —
communication uses pipe IPC (see core.services.pipe_ipc).

Supports warm worker pool: if USE_WARM_POOL=true, pre-spawned workers
are used for instant startup (~0.1s vs ~2.9s cold spawn).
"""

import asyncio
import json
import sys
import time as _time
from typing import Any, Dict, Optional

from loguru import logger


class SubprocessBotManager:
    """Manages subprocess lifecycle for isolated bot execution.

    Data flow:
        Telephony Provider <-WS-> Main Process (pipe relay) <-stdin/stdout-> Subprocess (bot_worker.py)
    """

    READY_TIMEOUT = 30  # seconds to wait for PIPE_READY signal

    @classmethod
    async def launch(
        cls,
        websocket: Any,
        agent_id: str,
        transport_type: str,
        call_data: Dict[str, Any],
        agent_data: Optional[Dict[str, Any]] = None,
    ):
        """Main entry point: try warm pool first, fall back to cold spawn.

        Args:
            websocket: The telephony provider's FastAPI WebSocket (already accepted).
            agent_id: UUID string of the agent to load in subprocess.
            transport_type: Telephony provider type (twilio, telnyx, exotel, plivo).
            call_data: Provider-specific call data dict.
            agent_data: Pre-serialized agent fields to skip DB query in subprocess.
        """
        # Try warm worker pool first
        warm_launched = await cls._try_warm_launch(
            websocket, agent_id, transport_type, call_data, agent_data
        )
        if warm_launched:
            return

        # Fall back to cold spawn (original path)
        await cls._cold_launch(websocket, agent_id, transport_type, call_data, agent_data)

    @classmethod
    async def _try_warm_launch(
        cls,
        websocket: Any,
        agent_id: str,
        transport_type: str,
        call_data: Dict[str, Any],
        agent_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Attempt to use a warm worker. Returns True if successful."""
        proc = None
        try:
            from core.services.warm_worker_pool import WarmWorkerPool
            pool = WarmWorkerPool.get_instance()
            worker = await pool.acquire()
            if worker is None:
                return False

            proc = worker["proc"]
            _t = _time.monotonic()

            # Send call data to the warm worker via stdin
            call_payload = json.dumps({
                "agent_id": str(agent_id),
                "transport_type": transport_type,
                "call_data": call_data,
                "agent_data": agent_data,
            }) + "\n"
            proc.stdin.write(call_payload.encode())
            await proc.stdin.drain()

            logger.info(
                "[TIMING] warm worker: sent call data to pid=%d (+%.3fs)",
                proc.pid, _time.monotonic() - _t,
            )

            # Wait for PIPE_READY (subprocess ready to receive frames)
            await cls._wait_for_signal(proc, "PIPE_READY")
            logger.info(
                "[TIMING] warm worker: total ready time (+%.3fs)",
                _time.monotonic() - _t,
            )

            try:
                await cls._proxy_pipes(websocket, proc)
            except Exception:
                logger.exception(
                    "SubprocessBotManager (warm) error for agent_id={}", agent_id
                )
            finally:
                await cls._cleanup(proc)
            return True

        except Exception as e:
            # Clean up the warm worker process if it was acquired but failed
            # to launch (e.g. _wait_for_signal timed out). Without this, the
            # orphaned process could keep running in the background.
            if proc:
                try:
                    await cls._cleanup(proc)
                except Exception:
                    pass
            logger.warning("Warm pool launch failed, falling back to cold spawn: %s", e)
            return False

    @classmethod
    async def _cold_launch(
        cls,
        websocket: Any,
        agent_id: str,
        transport_type: str,
        call_data: Dict[str, Any],
        agent_data: Optional[Dict[str, Any]] = None,
    ):
        """Cold-spawn path: spawn subprocess, wait for pipe ready, relay frames."""
        logger.info("[SubprocessBotManager] Cold launching for agent_id={}", agent_id)
        proc = None

        try:
            proc = await cls._spawn_worker(agent_id, transport_type, call_data, agent_data=agent_data)
            await cls._wait_for_signal(proc, "PIPE_READY")
            await cls._proxy_pipes(websocket, proc)
        except Exception:
            logger.exception(
                "SubprocessBotManager error for agent_id={}", agent_id
            )
        finally:
            if proc:
                await cls._cleanup(proc)

    @classmethod
    async def _spawn_worker(
        cls,
        agent_id: str,
        transport_type: str,
        call_data: Dict[str, Any],
        agent_data: Optional[Dict[str, Any]] = None,
    ) -> asyncio.subprocess.Process:
        """Spawn the bot_worker subprocess.

        stdin is piped for sending frames to the subprocess.
        stdout is piped for receiving PIPE_READY signal and frames from subprocess.
        stderr is inherited (None) so subprocess errors print to terminal.
        """
        call_data_json = json.dumps(call_data)
        cmd = [
            sys.executable,
            "-m",
            "core.bot_worker",
            "--agent_id",
            str(agent_id),
            "--transport_type",
            transport_type,
            "--call_data",
            call_data_json,
        ]
        if agent_data:
            cmd.extend(["--agent_data", json.dumps(agent_data)])
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=None,  # Inherit parent stderr so subprocess errors are visible
        )
        logger.info(
            "Spawned bot worker subprocess pid={} agent_id={}",
            proc.pid,
            agent_id,
        )
        return proc

    @classmethod
    async def _wait_for_signal(cls, proc: asyncio.subprocess.Process, signal: str):
        """Wait for the subprocess to send a text-line signal via stdout."""

        async def _read_stdout():
            while True:
                line = await proc.stdout.readline()
                if not line:
                    raise RuntimeError(
                        f"Bot worker subprocess exited before signaling {signal} (pid={proc.pid})"
                    )
                decoded = line.decode().strip()
                logger.debug("Bot worker stdout: {}", decoded)
                if decoded == signal:
                    return

        try:
            await asyncio.wait_for(_read_stdout(), timeout=cls.READY_TIMEOUT)
            logger.info("Bot worker signaled {} (pid={})", signal, proc.pid)
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"Bot worker subprocess did not signal {signal} within {cls.READY_TIMEOUT}s (pid={proc.pid})"
            )

    @classmethod
    async def _proxy_pipes(cls, telephony_ws: Any, proc: asyncio.subprocess.Process):
        """Bidirectional relay between telephony WS and subprocess stdin/stdout pipes.

        Uses the binary framing protocol from core.services.pipe_ipc.
        No internal WebSocket connection — frames go directly through OS pipes.
        """
        from core.services.pipe_ipc import FrameType, read_frame, write_frame

        async def telephony_to_subprocess():
            """Read from telephony WS, write framed messages to subprocess stdin.

            First drains stale buffered audio (media events queued during setup),
            then forwards all messages in real-time.
            """
            try:
                # Phase 1: Drain stale buffered audio
                drained = 0
                while True:
                    try:
                        msg = await asyncio.wait_for(telephony_ws.receive(), timeout=0.05)
                        msg_type = msg.get("type", "")
                        if msg_type == "websocket.disconnect":
                            logger.info("Telephony WebSocket disconnected during drain")
                            await write_frame(proc.stdin, FrameType.DISCONNECT)
                            return
                        if "text" in msg:
                            try:
                                payload = json.loads(msg["text"])
                                event = payload.get("event", "")
                                if event == "media":
                                    drained += 1
                                    continue
                            except (json.JSONDecodeError, TypeError):
                                pass
                            # Forward non-media messages (control events)
                            await write_frame(proc.stdin, FrameType.TEXT, msg["text"].encode("utf-8"))
                        elif "bytes" in msg:
                            drained += 1
                    except asyncio.TimeoutError:
                        break
                if drained:
                    logger.info("Drained {} stale audio messages from telephony WS buffer", drained)

                # Phase 2: Forward all messages in real-time
                while True:
                    msg = await telephony_ws.receive()
                    msg_type = msg.get("type", "")
                    if msg_type == "websocket.disconnect":
                        logger.info("Telephony WebSocket disconnected")
                        await write_frame(proc.stdin, FrameType.DISCONNECT)
                        break
                    if "text" in msg:
                        await write_frame(proc.stdin, FrameType.TEXT, msg["text"].encode("utf-8"))
                    elif "bytes" in msg:
                        await write_frame(proc.stdin, FrameType.BINARY, msg["bytes"])
            except Exception as e:
                logger.info("Telephony->subprocess pipe ended: {} ({})", type(e).__name__, e)

        async def subprocess_to_telephony():
            """Read framed messages from subprocess stdout, write to telephony WS."""
            try:
                while True:
                    ftype, data = await read_frame(proc.stdout)
                    if ftype == FrameType.TEXT:
                        await telephony_ws.send_text(data.decode("utf-8"))
                    elif ftype == FrameType.BINARY:
                        await telephony_ws.send_bytes(data)
                    elif ftype == FrameType.DISCONNECT:
                        logger.info("Subprocess signaled disconnect")
                        break
            except asyncio.IncompleteReadError:
                logger.info("Subprocess stdout EOF (process exited)")
            except Exception as e:
                logger.info("Subprocess->telephony pipe ended: {} ({})", type(e).__name__, e)

        # Start output relay IMMEDIATELY so bot audio reaches the telephony
        # provider without waiting for the input drain to finish
        output_task = asyncio.create_task(subprocess_to_telephony())
        input_task = asyncio.create_task(telephony_to_subprocess())

        proxy_tasks = [input_task, output_task]
        done, pending = await asyncio.wait(
            proxy_tasks, return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    @staticmethod
    async def _cleanup(proc: asyncio.subprocess.Process):
        """Terminate and clean up the subprocess."""
        if proc.returncode is not None:
            logger.info("Bot worker subprocess already exited (pid={} rc={})", proc.pid, proc.returncode)
            return

        logger.info("Terminating bot worker subprocess pid={}", proc.pid)
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=15)
            logger.info("Bot worker subprocess terminated (pid={})", proc.pid)
        except asyncio.TimeoutError:
            logger.warning("Bot worker subprocess did not terminate, killing pid={}", proc.pid)
            proc.kill()
            await proc.wait()
            logger.info("Bot worker subprocess killed (pid={})", proc.pid)
