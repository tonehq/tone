"""Binary framing protocol for subprocess IPC via stdin/stdout pipes.

Eliminates the WebSocket proxy + FastAPI/uvicorn in bot worker subprocesses.
The main process relays telephony WebSocket frames through the subprocess's
stdin/stdout using a lightweight binary protocol.

Frame format: [1 byte type][4 bytes payload length (big-endian)][payload]

Protocol phases:
    1. Text phase: subprocess prints ready signals as text lines on stdout
    2. Binary phase: after "PIPE_READY", both sides exchange framed messages
"""

import asyncio
import os
import struct
import sys
from enum import IntEnum
from typing import Tuple

from loguru import logger


class FrameType(IntEnum):
    """IPC frame types matching WebSocket message types."""

    TEXT = 0x01  # Text WebSocket message (payload: UTF-8 string)
    BINARY = 0x02  # Binary WebSocket message (payload: raw bytes)
    DISCONNECT = 0x03  # Peer disconnected (no payload)


HEADER_SIZE = 5  # 1 byte type + 4 bytes length


# ---------------------------------------------------------------------------
# Parent-side helpers (use asyncio StreamReader/StreamWriter from proc.stdin/stdout)
# ---------------------------------------------------------------------------


async def write_frame(
    writer: asyncio.StreamWriter, frame_type: FrameType, data: bytes = b""
):
    """Write a single framed message to an asyncio StreamWriter (parent side)."""
    header = struct.pack("!BI", frame_type, len(data))
    writer.write(header + data)
    await writer.drain()


async def read_frame(reader: asyncio.StreamReader) -> Tuple[FrameType, bytes]:
    """Read a single framed message. Raises IncompleteReadError on EOF."""
    header = await reader.readexactly(HEADER_SIZE)
    raw_type, length = struct.unpack("!BI", header)
    data = await reader.readexactly(length) if length > 0 else b""
    return FrameType(raw_type), data


# ---------------------------------------------------------------------------
# Subprocess-side: PipeWebSocket adapter
# ---------------------------------------------------------------------------


class PipeWebSocket:
    """WebSocket-compatible adapter backed by subprocess pipes.

    Implements the FastAPI WebSocket interface subset used by
    FastAPIWebsocketTransport: receive(), send_text(), send_bytes(),
    close(), client_state, application_state.
    """

    def __init__(self, reader: asyncio.StreamReader, write_fd: int):
        """
        Args:
            reader: Async reader connected to subprocess stdin.
            write_fd: Raw file descriptor for the IPC write pipe (original stdout).
        """
        self._reader = reader
        self._write_fd = write_fd
        self._connected = True
        self._write_lock = asyncio.Lock()

    @property
    def client_state(self):
        from starlette.websockets import WebSocketState

        return (
            WebSocketState.CONNECTED if self._connected else WebSocketState.DISCONNECTED
        )

    @property
    def application_state(self):
        from starlette.websockets import WebSocketState

        return (
            WebSocketState.CONNECTED if self._connected else WebSocketState.DISCONNECTED
        )

    async def receive(self) -> dict:
        """Read next frame, return in FastAPI WebSocket message format."""
        try:
            frame_type, data = await read_frame(self._reader)
            if frame_type == FrameType.TEXT:
                return {"type": "websocket.receive", "text": data.decode("utf-8")}
            elif frame_type == FrameType.BINARY:
                return {"type": "websocket.receive", "bytes": data}
            elif frame_type == FrameType.DISCONNECT:
                self._connected = False
                return {"type": "websocket.disconnect"}
            else:
                logger.warning("PipeWebSocket: unknown frame type %d", frame_type)
                self._connected = False
                return {"type": "websocket.disconnect"}
        except (asyncio.IncompleteReadError, ConnectionError, OSError):
            self._connected = False
            return {"type": "websocket.disconnect"}

    async def send_text(self, data: str):
        """Send a text message through the pipe."""
        if not self._connected:
            return
        try:
            await self._write_frame(FrameType.TEXT, data.encode("utf-8"))
        except (ConnectionError, OSError, BrokenPipeError):
            self._connected = False

    async def send_bytes(self, data: bytes):
        """Send a binary message through the pipe."""
        if not self._connected:
            return
        try:
            await self._write_frame(FrameType.BINARY, data)
        except (ConnectionError, OSError, BrokenPipeError):
            self._connected = False

    async def close(self):
        """Send disconnect frame and mark as disconnected."""
        if not self._connected:
            return
        self._connected = False
        try:
            await self._write_frame(FrameType.DISCONNECT, b"")
        except (ConnectionError, OSError, BrokenPipeError):
            pass

    async def _write_frame(self, frame_type: FrameType, data: bytes):
        """Write a framed message to the IPC pipe (thread-safe)."""
        header = struct.pack("!BI", frame_type, len(data))
        payload = header + data
        async with self._write_lock:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._blocking_write, payload)

    def _blocking_write(self, data: bytes):
        """Write all bytes to the pipe fd (blocking, called in executor)."""
        view = memoryview(data)
        offset = 0
        while offset < len(data):
            n = os.write(self._write_fd, view[offset:])
            if n == 0:
                raise BrokenPipeError("Pipe closed")
            offset += n


# ---------------------------------------------------------------------------
# Subprocess-side: setup helpers
# ---------------------------------------------------------------------------


def setup_subprocess_ipc() -> int:
    """Prepare subprocess for pipe-based IPC.

    Saves original stdout fd for binary IPC and redirects sys.stdout to
    stderr so that print() / logger stdout output doesn't corrupt the
    binary protocol.

    Returns:
        The IPC write file descriptor (original stdout).
    """
    ipc_write_fd = os.dup(sys.stdout.fileno())
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    sys.stdout = open(sys.stdout.fileno(), "w")
    return ipc_write_fd


def signal_pipe_ready(ipc_write_fd: int, signal: str = "PIPE_READY"):
    """Send a text-line ready signal to the parent process via IPC pipe."""
    os.write(ipc_write_fd, f"{signal}\n".encode())


def read_stdin_line() -> str:
    """Read one line from raw stdin fd (byte-by-byte, no Python buffering).

    Used by the warm worker to read call data JSON before switching to
    async pipe IPC. Byte-by-byte avoids Python's BufferedReader reading
    ahead and consuming binary frame data.
    """
    buf = bytearray()
    while True:
        b = os.read(0, 1)
        if not b or b == b"\n":
            break
        buf.extend(b)
    return buf.decode()


async def create_stdin_reader() -> asyncio.StreamReader:
    """Create an asyncio StreamReader connected to stdin for the subprocess.

    Uses raw fd 0 to avoid Python buffering issues (important when sync
    reads preceded this call, e.g. warm worker reading call data).
    """
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader(limit=2**20)  # 1 MB buffer
    protocol = asyncio.StreamReaderProtocol(reader)
    raw_stdin = open(0, "rb", buffering=0, closefd=False)
    await loop.connect_read_pipe(lambda: protocol, raw_stdin)
    return reader
