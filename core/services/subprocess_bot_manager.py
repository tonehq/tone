"""Process lifecycle manager for subprocess-based telephony bot isolation.

Spawns each telephony call as a separate OS process and proxies WebSocket
frames between the telephony provider's WebSocket and the subprocess's
local WebSocket.

Supports warm worker pool: if USE_WARM_POOL=true, pre-spawned workers
are used for instant startup (~0.1s vs ~2.9s cold spawn).
"""

import asyncio
import json
import socket
import sys
import time as _time
from typing import Any, Dict, Optional

from loguru import logger


class SubprocessBotManager:
    """Manages subprocess lifecycle for isolated bot execution.

    Data flow:
        Telephony Provider <-WS-> Main Process (proxy) <-WS (127.0.0.1)-> Subprocess (bot_worker.py)
    """

    READY_TIMEOUT = 30  # seconds to wait for WORKER_READY signal
    CONNECT_TIMEOUT = 15  # seconds to wait for subprocess WS connection
    CONNECT_RETRY_INTERVAL = 0.3  # seconds between connection retries

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
            port = worker["port"]
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
                "[TIMING] warm worker: sent call data to pid=%d port=%d (+%.3fs)",
                proc.pid, port, _time.monotonic() - _t,
            )

            # Wait for WORKER_READY (uvicorn started after receiving call data)
            await cls._wait_for_ready(proc, port)
            logger.info(
                "[TIMING] warm worker: total ready time (+%.3fs)",
                _time.monotonic() - _t,
            )

            try:
                await cls._proxy_websocket(websocket, port, proc)
            except Exception:
                logger.exception(
                    "SubprocessBotManager (warm) error for agent_id={} port={}", agent_id, port
                )
            finally:
                await cls._cleanup(proc)
            return True

        except Exception as e:
            # Clean up the warm worker process if it was acquired but failed
            # to launch (e.g. _wait_for_ready timed out). Without this, the
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
        """Original cold-spawn path (unchanged logic)."""
        print(f"[SubprocessBotManager] Cold launching for agent_id={agent_id}")
        port = cls._find_free_port()
        proc = None

        try:
            proc = await cls._spawn_worker(agent_id, transport_type, call_data, port, agent_data=agent_data)
            await cls._wait_for_ready(proc, port)
            await cls._proxy_websocket(websocket, port, proc)
        except Exception:
            logger.exception(
                "SubprocessBotManager error for agent_id={} port={}", agent_id, port
            )
        finally:
            if proc:
                await cls._cleanup(proc)

    @staticmethod
    def _find_free_port() -> int:
        """Find an available TCP port on localhost."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    @classmethod
    async def _spawn_worker(
        cls,
        agent_id: str,
        transport_type: str,
        call_data: Dict[str, Any],
        port: int,
        agent_data: Optional[Dict[str, Any]] = None,
    ) -> asyncio.subprocess.Process:
        """Spawn the bot_worker subprocess.

        stdout is piped so we can read the WORKER_READY signal.
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
            "--port",
            str(port),
        ]
        if agent_data:
            cmd.extend(["--agent_data", json.dumps(agent_data)])
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=None,  # Inherit parent stderr so subprocess errors are visible
        )
        logger.info(
            "Spawned bot worker subprocess pid={} port={} agent_id={}",
            proc.pid,
            port,
            agent_id,
        )
        return proc

    @classmethod
    async def _wait_for_ready(cls, proc: asyncio.subprocess.Process, port: int):
        """Wait for the subprocess to signal readiness via stdout."""
        ready_signal = f"WORKER_READY:{port}"

        async def _read_stdout():
            while True:
                line = await proc.stdout.readline()
                if not line:
                    raise RuntimeError(
                        f"Bot worker subprocess exited before signaling ready (pid={proc.pid})"
                    )
                decoded = line.decode().strip()
                logger.debug("Bot worker stdout: {}", decoded)
                if decoded == ready_signal:
                    return

        try:
            await asyncio.wait_for(_read_stdout(), timeout=cls.READY_TIMEOUT)
            logger.info("Bot worker ready on port {} (pid={})", port, proc.pid)
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"Bot worker subprocess did not signal ready within {cls.READY_TIMEOUT}s (pid={proc.pid})"
            )

    @classmethod
    async def _proxy_websocket(cls, telephony_ws: Any, subprocess_port: int, proc: asyncio.subprocess.Process):
        """Bidirectional WebSocket proxy between telephony WS and subprocess WS.

        Uses the websockets library (already a dependency via pipecat/uvicorn).
        """
        import websockets

        subprocess_url = f"ws://127.0.0.1:{subprocess_port}/ws"

        # Retry connection — WORKER_READY fires in on_startup before uvicorn
        # actually binds the port, so there's a brief window where connect fails.
        sub_ws = None
        deadline = asyncio.get_event_loop().time() + cls.CONNECT_TIMEOUT
        last_error = None
        while asyncio.get_event_loop().time() < deadline:
            try:
                sub_ws = await websockets.connect(
                    subprocess_url,
                    open_timeout=cls.CONNECT_TIMEOUT,
                )
                break
            except (ConnectionRefusedError, OSError) as e:
                # Port not ready yet — retry
                last_error = e
                await asyncio.sleep(cls.CONNECT_RETRY_INTERVAL)
            except Exception as e:
                last_error = e
                await asyncio.sleep(cls.CONNECT_RETRY_INTERVAL)

        if sub_ws is None:
            raise RuntimeError(
                f"Could not connect to subprocess WebSocket at {subprocess_url} "
                f"after {cls.CONNECT_TIMEOUT}s: {last_error}"
            )

        logger.info("Connected to subprocess WebSocket at {}", subprocess_url)

        try:
            async def telephony_to_subprocess():
                """Forward frames from telephony provider to subprocess.

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
                                await sub_ws.send(msg["text"])
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
                            break
                        if "text" in msg:
                            await sub_ws.send(msg["text"])
                        elif "bytes" in msg:
                            await sub_ws.send(msg["bytes"])
                except Exception as e:
                    logger.info("Telephony->subprocess proxy ended: {} ({})", type(e).__name__, e)

            async def subprocess_to_telephony():
                """Forward frames from subprocess to telephony provider."""
                try:
                    async for message in sub_ws:
                        if isinstance(message, str):
                            await telephony_ws.send_text(message)
                        elif isinstance(message, bytes):
                            await telephony_ws.send_bytes(message)
                except Exception as e:
                    logger.info("Subprocess->telephony proxy ended: {} ({})", type(e).__name__, e)

            async def _drain_stdout():
                """Keep reading subprocess stdout so the pipe buffer doesn't fill
                up and block the subprocess (classic pipe deadlock)."""
                try:
                    while True:
                        line = await proc.stdout.readline()
                        if not line:
                            break
                        logger.debug("Bot worker: {}", line.decode().strip())
                except Exception:
                    pass

            # Start output proxy + stdout drain IMMEDIATELY so bot audio
            # reaches Twilio without waiting for the input drain to finish
            drain_task = asyncio.create_task(_drain_stdout())
            output_task = asyncio.create_task(subprocess_to_telephony())

            # Run input proxy concurrently with the already-running output proxy
            proxy_tasks = [
                asyncio.create_task(telephony_to_subprocess()),
                output_task,
            ]
            done, pending = await asyncio.wait(
                proxy_tasks, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            drain_task.cancel()
            try:
                await drain_task
            except asyncio.CancelledError:
                pass

        finally:
            try:
                await sub_ws.close()
            except Exception:
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
