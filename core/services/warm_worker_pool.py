"""Pre-spawned worker pool for subprocess-based bot isolation.

Maintains a pool of idle Python subprocesses that have already imported
pipecat and heavy dependencies. When a call arrives, a warm worker is
claimed instantly (~0.1s) instead of cold-spawning a new process (~2.9s).

Workers are one-shot: after handling a call they are discarded and a
replacement is pre-spawned in the background.
"""

import asyncio
import json
import socket
import sys
import time as _time
from typing import Optional

from loguru import logger


class WarmWorkerPool:
    """Pool of pre-spawned bot worker subprocesses ready to accept calls."""

    _instance: Optional["WarmWorkerPool"] = None
    _lock = asyncio.Lock()

    def __init__(self, pool_size: int = 2):
        self._pool_size = pool_size
        self._workers: asyncio.Queue = asyncio.Queue()
        self._started = False
        self._replenish_task: Optional[asyncio.Task] = None

    @classmethod
    def get_instance(cls, pool_size: int = 2) -> "WarmWorkerPool":
        """Get or create the singleton pool instance."""
        if cls._instance is None:
            cls._instance = cls(pool_size=pool_size)
        return cls._instance

    async def start(self):
        """Pre-spawn workers to fill the pool. Call once at server startup."""
        if self._started:
            return
        self._started = True
        logger.info("WarmWorkerPool: pre-spawning {} workers...", self._pool_size)
        tasks = [self._spawn_warm_worker() for _ in range(self._pool_size)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        ready_count = sum(1 for r in results if not isinstance(r, Exception))
        logger.info("WarmWorkerPool: {} workers ready", ready_count)

    async def acquire(self) -> Optional[dict]:
        """Get a warm worker from the pool, or None if pool is empty.

        Returns dict with keys: proc, port, stdin_writer
        After acquiring, the caller should send call data and proxy the WS.
        A replacement worker is spawned in the background.
        """
        try:
            worker = self._workers.get_nowait()
            # Verify the worker is still alive
            if worker["proc"].returncode is not None:
                logger.warning("WarmWorkerPool: acquired worker pid=%d already exited, discarding", worker["proc"].pid)
                self._schedule_replenish(1)
                return None
            logger.info("WarmWorkerPool: acquired warm worker pid=%d port=%d", worker["proc"].pid, worker["port"])
            # Replenish in background
            self._schedule_replenish(1)
            return worker
        except asyncio.QueueEmpty:
            logger.warning("WarmWorkerPool: no warm workers available, cold spawn needed")
            return None

    async def shutdown(self):
        """Terminate all idle workers in the pool."""
        terminated = 0
        while not self._workers.empty():
            try:
                worker = self._workers.get_nowait()
                proc = worker["proc"]
                if proc.returncode is None:
                    proc.terminate()
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=3)
                    except asyncio.TimeoutError:
                        proc.kill()
                        await proc.wait()
                    terminated += 1
            except asyncio.QueueEmpty:
                break
        if self._replenish_task and not self._replenish_task.done():
            self._replenish_task.cancel()
        self._started = False
        logger.info("WarmWorkerPool: shut down %d workers", terminated)

    def _schedule_replenish(self, count: int):
        """Schedule background replenishment of the pool."""
        asyncio.create_task(self._replenish(count))

    async def _replenish(self, count: int):
        """Spawn replacement workers in the background."""
        for _ in range(count):
            try:
                await self._spawn_warm_worker()
            except Exception as e:
                logger.warning("WarmWorkerPool: failed to replenish worker: %s", e)

    async def _spawn_warm_worker(self):
        """Spawn a single warm worker subprocess that imports everything and waits."""
        port = self._find_free_port()
        _t = _time.monotonic()

        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "core.warm_worker",
            "--port",
            str(port),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=None,  # Inherit parent stderr
        )

        # Wait for WARM_READY signal
        ready_signal = f"WARM_READY:{port}"
        try:
            while True:
                line = await asyncio.wait_for(proc.stdout.readline(), timeout=30)
                if not line:
                    raise RuntimeError(f"Warm worker exited before ready (pid={proc.pid})")
                decoded = line.decode().strip()
                if decoded == ready_signal:
                    break
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise RuntimeError(f"Warm worker did not signal ready in 30s (pid={proc.pid})")

        elapsed = _time.monotonic() - _t
        logger.info("WarmWorkerPool: worker pid=%d port=%d ready in %.2fs", proc.pid, port, elapsed)

        worker = {"proc": proc, "port": port}
        await self._workers.put(worker)
        return worker

    @staticmethod
    def _find_free_port() -> int:
        """Find an available TCP port on localhost."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]
