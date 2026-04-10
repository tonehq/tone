"""
Twilio Load Test — Simulates How Pipecat Handles Concurrent Calls (Subprocess Model)
=====================================================================================
Pipecat now handles each incoming call by spawning a **separate subprocess** via
SubprocessBotManager.spawn_bot(). Each call = 1 dedicated Python process running
the bot pipeline (STT -> LLM -> TTS).

This script:
  1. Triggers outbound Twilio calls that hit your /ws webhook
  2. Each call causes the server to spawn a subprocess (core.bot_worker)
  3. Monitors subprocess count via the /calls API endpoint and psutil
  4. Tracks per-process resource usage (CPU, memory) for each bot subprocess
  5. Verifies the /status endpoint receives call lifecycle callbacks

Usage:
    # Trigger 5 concurrent calls and watch subprocess spawning
    python tools/twilio_load_test.py --calls 5 \
        --to-number "+1234567890" --webhook-url "https://your-server.com/voice"

    # Gradual load test: 2 -> 5 -> 10 -> 15 -> 20
    python tools/twilio_load_test.py --mode load_test \
        --to-number "+1234567890" --webhook-url "https://your-server.com/voice"

    # With delay between calls (staggered)
    python tools/twilio_load_test.py --calls 10 --delay 1.0 \
        --to-number "+1234567890" --webhook-url "https://your-server.com/voice"

    # Monitor running bot subprocesses without triggering calls
    python tools/twilio_load_test.py --mode monitor --server-pid 12345

    # Specify the server base URL for /calls and /status endpoint checks
    python tools/twilio_load_test.py --calls 5 \
        --to-number "+1234567890" --webhook-url "https://your-server.com/voice" \
        --server-url "http://localhost:7860"

Environment Variables:
    TWILIO_ACCOUNT_SID    - Twilio account SID
    TWILIO_AUTH_TOKEN      - Twilio auth token
    TWILIO_PHONE_NUMBER   - Twilio phone number (E.164 format)
"""

import argparse
import asyncio
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import httpx
import psutil
from dotenv import load_dotenv
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("twilio_load_test")

# Pattern to identify bot worker subprocesses
BOT_WORKER_PATTERN = "core.bot_worker"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class CallConfig:
    """Parameters for a batch of calls."""
    from_number: str
    to_number: str
    webhook_url: str
    num_calls: int = 5
    delay: float = 0.0       # seconds between initiating calls
    call_duration: int = 30   # how long to let calls run before checking status
    server_pid: Optional[int] = None  # PID of your running Pipecat server
    server_url: str = "http://localhost:7860"  # Base URL for /calls and /status endpoints


@dataclass
class CallResult:
    """Outcome of a single Twilio call attempt."""
    call_index: int = 0
    call_sid: Optional[str] = None
    status: str = "not_started"
    timestamp: str = ""
    error: Optional[str] = None
    api_latency_ms: float = 0.0


@dataclass
class BotProcessInfo:
    """Info about a single bot worker subprocess."""
    pid: int
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    cmdline: str = ""
    create_time: float = 0.0


@dataclass
class ApiCallInfo:
    """Info about an active call from the /calls API endpoint."""
    pid: int = 0
    agent_id: int = 0
    transport_type: str = ""
    stream_id: str = ""
    call_sid: str = ""
    started_at: float = 0.0
    alive: bool = True


@dataclass
class ServerSnapshot:
    """Resource snapshot of the Pipecat backend server + its bot subprocesses."""
    timestamp: str = ""
    server_pid: int = 0
    server_cpu_percent: float = 0.0
    server_memory_mb: float = 0.0
    server_threads: int = 0
    server_connections: int = 0
    bot_subprocess_count: int = 0
    bot_processes: list[BotProcessInfo] = field(default_factory=list)
    total_bot_cpu: float = 0.0
    total_bot_memory_mb: float = 0.0
    api_call_count: int = 0  # from /calls endpoint
    api_calls: list[ApiCallInfo] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Twilio client
# ---------------------------------------------------------------------------
def get_twilio_client() -> Client:
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    if not account_sid or not auth_token:
        logger.error("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set")
        sys.exit(1)
    return Client(account_sid, auth_token)


def default_from_number() -> str:
    number = os.getenv("TWILIO_PHONE_NUMBER", "")
    if not number:
        logger.error("TWILIO_PHONE_NUMBER must be set")
        sys.exit(1)
    return number


# ---------------------------------------------------------------------------
# /calls API endpoint — query SubprocessBotManager.get_active_calls()
# ---------------------------------------------------------------------------
async def fetch_active_calls(server_url: str) -> list[ApiCallInfo]:
    """Query the /calls endpoint to get active subprocess info from SubprocessBotManager.

    This is the primary way to check how many subprocesses are running, rather
    than relying solely on ps aux. The endpoint returns data directly from
    SubprocessBotManager's tracking dicts.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{server_url}/calls")
            if resp.status_code == 200:
                data = resp.json()
                return [
                    ApiCallInfo(
                        pid=c.get("pid", 0),
                        agent_id=c.get("agent_id", 0),
                        transport_type=c.get("transport_type", ""),
                        stream_id=c.get("stream_id", ""),
                        call_sid=c.get("call_sid", ""),
                        started_at=c.get("started_at", 0.0),
                        alive=c.get("alive", True),
                    )
                    for c in data
                ]
            else:
                logger.warning("/calls returned status %d", resp.status_code)
                return []
    except Exception as e:
        logger.debug("/calls endpoint unavailable: %s", e)
        return []


async def check_status_endpoint(server_url: str) -> bool:
    """Verify the /status endpoint exists and doesn't return 404.

    The /status endpoint receives call lifecycle callbacks from Twilio.
    Before the subprocess architecture changes, this would return 404.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Send a minimal POST to /status — it should return 200
            resp = await client.post(f"{server_url}/status", content=b"")
            if resp.status_code == 200:
                return True
            elif resp.status_code == 404:
                logger.warning("/status endpoint returned 404 — not registered")
                return False
            else:
                logger.warning("/status returned status %d", resp.status_code)
                return resp.status_code != 404
    except Exception as e:
        logger.debug("/status endpoint unavailable: %s", e)
        return False


# ---------------------------------------------------------------------------
# Subprocess enumeration — find bot_worker processes via ps aux style
# ---------------------------------------------------------------------------
def find_bot_worker_processes() -> list[BotProcessInfo]:
    """Find all running bot_worker subprocesses by scanning process list.

    This is the equivalent of running:
        ps aux | grep core.bot_worker

    Each SubprocessBotManager.spawn_bot() call creates one of these processes.
    """
    bot_processes = []
    for proc in psutil.process_iter(["pid", "cmdline", "cpu_percent", "memory_info", "create_time"]):
        try:
            cmdline = " ".join(proc.info["cmdline"] or [])
            if BOT_WORKER_PATTERN in cmdline:
                mem_mb = round(proc.info["memory_info"].rss / (1024 * 1024), 1) if proc.info["memory_info"] else 0.0
                bot_processes.append(BotProcessInfo(
                    pid=proc.info["pid"],
                    cpu_percent=proc.cpu_percent(interval=0),
                    memory_mb=mem_mb,
                    cmdline=cmdline,
                    create_time=proc.info["create_time"] or 0.0,
                ))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return bot_processes


def run_ps_aux_grep() -> str:
    """Run actual `ps aux | grep core.bot_worker` and return output.

    Provides the raw ps aux view so you can cross-reference with psutil data.
    """
    try:
        result = subprocess.run(
            ["bash", "-c", f"ps aux | grep '{BOT_WORKER_PATTERN}' | grep -v grep"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip()
    except Exception as e:
        return f"(ps aux failed: {e})"


# ---------------------------------------------------------------------------
# Server + subprocess monitoring
# ---------------------------------------------------------------------------
async def take_server_snapshot(pid: int, server_url: str = "http://localhost:7860") -> Optional[ServerSnapshot]:
    """Capture resource metrics from the server AND all bot subprocesses.

    Uses both psutil (OS-level process scanning) and the /calls API endpoint
    (SubprocessBotManager's internal tracking) for comprehensive monitoring.

    In the subprocess model:
    - The main server process (uvicorn) stays lightweight — it just proxies WebSocket
    - Each call spawns a separate bot_worker subprocess with its own memory/CPU
    - Subprocess count = number of active calls being handled
    """
    try:
        proc = psutil.Process(pid)
        bot_processes = find_bot_worker_processes()

        total_bot_cpu = sum(bp.cpu_percent for bp in bot_processes)
        total_bot_mem = sum(bp.memory_mb for bp in bot_processes)

        # Also query /calls endpoint for SubprocessBotManager's view
        api_calls = await fetch_active_calls(server_url)

        return ServerSnapshot(
            timestamp=datetime.now(timezone.utc).strftime("%H:%M:%S"),
            server_pid=pid,
            server_cpu_percent=proc.cpu_percent(interval=0.5),
            server_memory_mb=round(proc.memory_info().rss / (1024 * 1024), 1),
            server_threads=proc.num_threads(),
            server_connections=len(proc.net_connections(kind="inet")),
            bot_subprocess_count=len(bot_processes),
            bot_processes=bot_processes,
            total_bot_cpu=round(total_bot_cpu, 1),
            total_bot_memory_mb=round(total_bot_mem, 1),
            api_call_count=len(api_calls),
            api_calls=api_calls,
        )
    except psutil.NoSuchProcess:
        logger.error("Server process %d not found. Is your backend running?", pid)
        return None
    except psutil.AccessDenied:
        logger.error("Access denied to process %d. Try running with sudo.", pid)
        return None


def print_server_snapshot(snap: ServerSnapshot, label: str = "") -> None:
    prefix = f"[{label}] " if label else ""
    print(
        f"  {prefix}{snap.timestamp}  "
        f"Server: CPU={snap.server_cpu_percent:5.1f}%  MEM={snap.server_memory_mb:7.1f}MB  "
        f"Threads={snap.server_threads:3d}  Conns={snap.server_connections:3d}  |  "
        f"Bot Subprocesses: {snap.bot_subprocess_count:3d} (psutil)  "
        f"{snap.api_call_count:3d} (/calls)  "
        f"TotalCPU={snap.total_bot_cpu:5.1f}%  TotalMEM={snap.total_bot_memory_mb:7.1f}MB"
    )


def print_subprocess_details(snap: ServerSnapshot) -> None:
    """Print per-subprocess details (like a focused ps aux output)."""
    if not snap.bot_processes:
        print("    (no bot_worker subprocesses running)")
        return

    print(f"    {'PID':>7}  {'CPU%':>6}  {'MEM(MB)':>8}  {'Started':>10}  Command")
    print(f"    {'─' * 7}  {'─' * 6}  {'─' * 8}  {'─' * 10}  {'─' * 40}")
    for bp in snap.bot_processes:
        started = datetime.fromtimestamp(bp.create_time).strftime("%H:%M:%S") if bp.create_time else "?"
        # Truncate command line for readability
        cmd_short = bp.cmdline[:80] + "..." if len(bp.cmdline) > 80 else bp.cmdline
        print(f"    {bp.pid:>7}  {bp.cpu_percent:>5.1f}%  {bp.memory_mb:>7.1f}  {started:>10}  {cmd_short}")

    # Also show /calls API data if available and differs from psutil
    if snap.api_calls:
        api_pids = {c.pid for c in snap.api_calls}
        ps_pids = {bp.pid for bp in snap.bot_processes}
        if api_pids != ps_pids:
            print(f"\n    /calls API shows different PIDs than psutil:")
            print(f"      psutil: {sorted(ps_pids)}")
            print(f"      /calls: {sorted(api_pids)}")

        print(f"\n    /calls API details:")
        print(f"    {'PID':>7}  {'AgentID':>8}  {'Transport':>10}  {'StreamID':>20}  {'CallSID':>20}  {'Alive':>6}")
        print(f"    {'─' * 7}  {'─' * 8}  {'─' * 10}  {'─' * 20}  {'─' * 20}  {'─' * 6}")
        for c in snap.api_calls:
            stream_short = c.stream_id[:20] if c.stream_id else ""
            call_short = c.call_sid[:20] if c.call_sid else ""
            print(f"    {c.pid:>7}  {c.agent_id:>8}  {c.transport_type:>10}  {stream_short:>20}  {call_short:>20}  {'yes' if c.alive else 'no':>6}")


def find_server_pid() -> Optional[int]:
    """Try to auto-detect the Pipecat/uvicorn server process."""
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmdline = " ".join(proc.info["cmdline"] or [])
            if "uvicorn" in cmdline and ("main:app" in cmdline or "main_ee:app" in cmdline):
                return proc.info["pid"]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


# ---------------------------------------------------------------------------
# Core: initiate a single call via Twilio API
# ---------------------------------------------------------------------------
async def initiate_call_async(
    client: Client,
    from_number: str,
    to_number: str,
    webhook_url: str,
    call_index: int,
) -> CallResult:
    """Place one outbound call via Twilio.

    When Twilio connects to your /ws endpoint, SubprocessBotManager.spawn_bot()
    will spawn a dedicated subprocess (core.bot_worker) for this call.
    Each call = 1 separate OS process, visible via `ps aux | grep core.bot_worker`
    or via the GET /calls endpoint.

    The status_callback is set to /status so Twilio posts call lifecycle events
    which trigger SubprocessBotManager.handle_call_status() for cleanup.
    """
    ts = datetime.now(timezone.utc).isoformat()
    start = time.perf_counter()

    loop = asyncio.get_running_loop()
    try:
        call = await loop.run_in_executor(
            None,
            lambda: client.calls.create(
                to=to_number,
                from_=from_number,
                url=webhook_url,
                method="POST",
                status_callback=webhook_url.rstrip("/") + "/status",
                status_callback_method="POST",
                status_callback_event=["initiated", "ringing", "answered", "completed"],
            ),
        )
        elapsed = (time.perf_counter() - start) * 1000
        logger.info(
            "Call #%d  SID=%s  status=%s  latency=%.0fms",
            call_index, call.sid, call.status, elapsed,
        )
        return CallResult(
            call_index=call_index,
            call_sid=call.sid,
            status=call.status,
            timestamp=ts,
            api_latency_ms=round(elapsed, 1),
        )

    except TwilioRestException as exc:
        elapsed = (time.perf_counter() - start) * 1000
        logger.error("Call #%d  Twilio error %d: %s", call_index, exc.code, exc.msg)
        return CallResult(
            call_index=call_index, status="failed", timestamp=ts,
            error=f"TwilioError({exc.code}): {exc.msg}",
            api_latency_ms=round(elapsed, 1),
        )
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        logger.error("Call #%d  Unexpected error: %s", call_index, exc)
        return CallResult(
            call_index=call_index, status="failed", timestamp=ts,
            error=str(exc), api_latency_ms=round(elapsed, 1),
        )


# ---------------------------------------------------------------------------
# Poll call status — check subprocesses spawned per call
# ---------------------------------------------------------------------------
async def poll_call_status(
    client: Client,
    call_sids: list[str],
    duration: int,
    server_pid: Optional[int],
    server_url: str = "http://localhost:7860",
) -> dict[str, str]:
    """Monitor active calls and bot subprocesses while calls are running.

    Uses both /calls API endpoint and psutil for subprocess tracking:
    - /calls endpoint: SubprocessBotManager's internal view (pid, agent_id, call_sid)
    - psutil: OS-level process scanning (CPU, memory per subprocess)
    - ps aux: raw verification

    The /status endpoint receives Twilio callbacks that trigger
    SubprocessBotManager.handle_call_status() for automatic cleanup
    on terminal statuses (completed, failed, busy, no-answer, canceled).
    """
    logger.info("Monitoring %d active calls for %ds...", len(call_sids), duration)
    print()

    loop = asyncio.get_running_loop()
    interval = 3  # poll every 3 seconds
    elapsed = 0

    while elapsed < duration:
        # Server + subprocess snapshot (includes /calls API data)
        if server_pid:
            snap = await take_server_snapshot(server_pid, server_url)
            if snap:
                print_server_snapshot(snap, f"t+{elapsed:3d}s")

        # Also show raw ps aux output periodically
        if elapsed % 9 == 0:  # every 3rd poll
            ps_output = run_ps_aux_grep()
            if ps_output:
                print(f"\n    [ps aux | grep {BOT_WORKER_PATTERN}]")
                for line in ps_output.split("\n"):
                    print(f"    {line}")
                print()

        # Check call statuses via Twilio API
        active = 0
        for sid in call_sids:
            try:
                call = await loop.run_in_executor(
                    None, lambda s=sid: client.calls(s).fetch()
                )
                if call.status in ("queued", "ringing", "in-progress"):
                    active += 1
            except Exception:
                pass

        # Cross-reference: /calls endpoint vs Twilio active count
        api_calls = await fetch_active_calls(server_url)
        bot_count = len(find_bot_worker_processes())
        logger.info(
            "  Active Twilio calls: %d / %d  |  Bot subprocesses: %d (psutil)  %d (/calls)",
            active, len(call_sids), bot_count, len(api_calls),
        )
        if active == 0 and elapsed > 5:
            logger.info("  All calls ended.")
            break

        await asyncio.sleep(interval)
        elapsed += interval

    # Fetch final statuses
    final_statuses = {}
    for sid in call_sids:
        try:
            call = await loop.run_in_executor(
                None, lambda s=sid: client.calls(s).fetch()
            )
            final_statuses[sid] = call.status
        except Exception:
            final_statuses[sid] = "unknown"

    return final_statuses


# ---------------------------------------------------------------------------
# Main test runner — triggers calls that spawn subprocesses
# ---------------------------------------------------------------------------
async def run_concurrent_calls(config: CallConfig) -> list[CallResult]:
    """Fire N calls concurrently. Each call triggers SubprocessBotManager.spawn_bot()
    on the server, which spawns a dedicated core.bot_worker subprocess.

    After triggering calls, monitors:
    - Number of bot subprocesses via /calls API endpoint and psutil
    - Per-subprocess CPU and memory usage
    - Raw `ps aux | grep core.bot_worker` output for manual verification
    - /status endpoint availability (should return 200, not 404)
    """
    client = get_twilio_client()
    server_pid = config.server_pid or find_server_pid()

    print(f"\n{'=' * 80}")
    print(f"  Pipecat Load Test — {config.num_calls} concurrent calls (Subprocess-per-Call Model)")
    print(f"  Model: Each call = 1 subprocess via SubprocessBotManager.spawn_bot()")
    print(f"  From: {config.from_number}  To: {config.to_number}")
    print(f"  Webhook: {config.webhook_url}")
    print(f"  Server URL: {config.server_url}")
    if server_pid:
        print(f"  Monitoring server PID: {server_pid}")
    else:
        print(f"  Server PID: not found (use --server-pid to enable monitoring)")
    print(f"  Verify with: ps aux | grep {BOT_WORKER_PATTERN}")
    print(f"  Or query: curl {config.server_url}/calls")
    print(f"{'=' * 80}\n")

    # Verify /status endpoint is registered (should not be 404)
    status_ok = await check_status_endpoint(config.server_url)
    if status_ok:
        print(f"  /status endpoint: OK (Twilio callbacks will trigger subprocess cleanup)")
    else:
        print(f"  /status endpoint: NOT FOUND — subprocess cleanup will rely on WS disconnect only")
    print()

    # Check /calls endpoint
    api_calls_before = await fetch_active_calls(config.server_url)
    print(f"  /calls endpoint: {len(api_calls_before)} active calls before test")

    # Snapshot before calls — should show 0 bot subprocesses
    if server_pid:
        snap = await take_server_snapshot(server_pid, config.server_url)
        if snap:
            print("  BEFORE calls:")
            print_server_snapshot(snap)
            print_subprocess_details(snap)
            print()

    # Fire all calls — each will cause a subprocess to be spawned on the server
    tasks: list[asyncio.Task] = []
    for i in range(config.num_calls):
        if config.delay > 0 and i > 0:
            await asyncio.sleep(config.delay)
        task = asyncio.create_task(
            initiate_call_async(client, config.from_number, config.to_number,
                                config.webhook_url, i + 1)
        )
        tasks.append(task)

    results = list(await asyncio.gather(*tasks))

    # Brief pause to let subprocesses spawn
    logger.info("Waiting 3s for subprocesses to spawn...")
    await asyncio.sleep(3)

    # Show subprocess state right after calls connect
    if server_pid:
        snap = await take_server_snapshot(server_pid, config.server_url)
        if snap:
            print("\n  AFTER call initiation (subprocesses should be spawning):")
            print_server_snapshot(snap)
            print_subprocess_details(snap)
            print()

    # Show raw ps aux
    ps_output = run_ps_aux_grep()
    if ps_output:
        print(f"  [ps aux | grep {BOT_WORKER_PATTERN}]")
        for line in ps_output.split("\n"):
            print(f"    {line}")
        print()

    # Collect successful call SIDs for monitoring
    call_sids = [r.call_sid for r in results if r.call_sid]

    # Monitor active calls and subprocess count
    if call_sids:
        final_statuses = await poll_call_status(
            client, call_sids, config.call_duration, server_pid, config.server_url
        )
    else:
        final_statuses = {}

    # Snapshot after calls end — subprocesses should be cleaned up
    if server_pid:
        snap = await take_server_snapshot(server_pid, config.server_url)
        if snap:
            print("\n  AFTER calls completed:")
            print_server_snapshot(snap)
            print_subprocess_details(snap)

    # Check /calls endpoint after completion — should show 0
    api_calls_after = await fetch_active_calls(config.server_url)
    print(f"\n  /calls endpoint: {len(api_calls_after)} active calls after test")
    if api_calls_after:
        print(f"    WARNING: subprocesses still tracked — cleanup may be delayed")
        for c in api_calls_after:
            print(f"      pid={c.pid} call_sid={c.call_sid} alive={c.alive}")

    # Print summary
    _print_summary(results, final_statuses, server_pid, config.server_url)
    return results


# ---------------------------------------------------------------------------
# Load test: gradual ramp-up
# ---------------------------------------------------------------------------
async def run_load_test(config: CallConfig) -> None:
    """Ramp up calls gradually to observe subprocess spawning under increasing load.

    Stages: 2 -> 5 -> 10 -> 15 -> 20 concurrent calls
    Shows how the subprocess-per-call model scales:
    - Each call spawns a separate process via SubprocessBotManager.spawn_bot()
    - Process count should match active call count (check /calls endpoint)
    - Memory is isolated per subprocess (no shared pipeline state)
    - CPU load distributes across subprocesses (multi-core utilization)
    """
    stages = [2, 5, 10, 15, 20]
    server_pid = config.server_pid or find_server_pid()

    print(f"\n{'=' * 80}")
    print(f"  LOAD TEST — Gradual ramp-up: {stages}")
    print(f"  Testing Pipecat's subprocess-per-call concurrency model")
    print(f"  Each call = 1 subprocess (core.bot_worker)")
    print(f"  Verify with: ps aux | grep {BOT_WORKER_PATTERN}")
    print(f"  Or query: curl {config.server_url}/calls")
    print(f"{'=' * 80}\n")

    stage_results = []

    for stage_num, stage_calls in enumerate(stages, 1):
        print(f"\n{'─' * 80}")
        print(f"  STAGE {stage_num}: {stage_calls} concurrent calls ({stage_calls} subprocesses expected)")
        print(f"{'─' * 80}")

        # Snapshot before
        snap_before = await take_server_snapshot(server_pid, config.server_url) if server_pid else None
        procs_before = len(find_bot_worker_processes())
        api_before = len(await fetch_active_calls(config.server_url))

        stage_config = CallConfig(
            from_number=config.from_number,
            to_number=config.to_number,
            webhook_url=config.webhook_url,
            num_calls=stage_calls,
            delay=config.delay,
            call_duration=config.call_duration,
            server_pid=server_pid,
            server_url=config.server_url,
        )

        start = time.perf_counter()
        results = await run_concurrent_calls(stage_config)
        elapsed = time.perf_counter() - start

        # Snapshot after
        snap_after = await take_server_snapshot(server_pid, config.server_url) if server_pid else None
        procs_after = len(find_bot_worker_processes())
        api_after = len(await fetch_active_calls(config.server_url))

        succeeded = sum(1 for r in results if r.status != "failed")
        avg_latency = (
            sum(r.api_latency_ms for r in results) / len(results) if results else 0
        )

        stage_results.append({
            "calls": stage_calls,
            "succeeded": succeeded,
            "failed": len(results) - succeeded,
            "avg_latency_ms": avg_latency,
            "wall_time_s": elapsed,
            "server_mem_before": snap_before.server_memory_mb if snap_before else 0,
            "server_mem_after": snap_after.server_memory_mb if snap_after else 0,
            "bot_procs_before": procs_before,
            "bot_procs_after": procs_after,
            "api_calls_before": api_before,
            "api_calls_after": api_after,
            "total_bot_mem": snap_after.total_bot_memory_mb if snap_after else 0,
            "total_bot_cpu": snap_after.total_bot_cpu if snap_after else 0,
        })

        # Cooldown between stages — let subprocesses clean up
        if stage_num < len(stages):
            cooldown = 10
            logger.info("Cooling down %ds before next stage (waiting for subprocess cleanup)...", cooldown)
            await asyncio.sleep(cooldown)
            remaining = len(find_bot_worker_processes())
            remaining_api = len(await fetch_active_calls(config.server_url))
            logger.info("Bot subprocesses remaining after cooldown: %d (psutil) %d (/calls)", remaining, remaining_api)

    # Final comparison table
    print(f"\n{'=' * 80}")
    print(f"  LOAD TEST RESULTS — Subprocess-per-Call Model")
    print(f"{'=' * 80}")
    print(f"  {'Calls':>5}  {'OK':>4}  {'Fail':>4}  {'Avg Latency':>12}  "
          f"{'Wall Time':>10}  {'Server MEM':>14}  {'BotProcs':>10}  {'API Calls':>10}  {'Bot MEM':>10}  {'Bot CPU':>8}")
    print(f"  {'─' * 5}  {'─' * 4}  {'─' * 4}  {'─' * 12}  "
          f"{'─' * 10}  {'─' * 14}  {'─' * 10}  {'─' * 10}  {'─' * 10}  {'─' * 8}")

    for s in stage_results:
        svr_mem = f"{s['server_mem_before']:.0f}->{s['server_mem_after']:.0f}MB"
        procs = f"{s['bot_procs_before']}->{s['bot_procs_after']}"
        api = f"{s['api_calls_before']}->{s['api_calls_after']}"
        print(
            f"  {s['calls']:>5}  {s['succeeded']:>4}  {s['failed']:>4}  "
            f"{s['avg_latency_ms']:>9.0f}ms   {s['wall_time_s']:>8.1f}s  "
            f"{svr_mem:>14}  {procs:>10}  {api:>10}  "
            f"{s['total_bot_mem']:>8.1f}MB  {s['total_bot_cpu']:>6.1f}%"
        )

    print(f"\n  Key observations (Subprocess Model):")
    print(f"  - Each call spawns 1 subprocess via SubprocessBotManager.spawn_bot()")
    print(f"  - Bot process count should match active call count")
    print(f"    Check: ps aux | grep {BOT_WORKER_PATTERN}")
    print(f"    Check: curl {config.server_url}/calls")
    print(f"  - /status endpoint receives Twilio callbacks for automatic subprocess cleanup")
    print(f"  - Server process stays lightweight (just proxies WebSocket <-> subprocess stdin/stdout)")
    print(f"  - Each subprocess has isolated memory (no shared state between calls)")
    print(f"  - Multi-core CPU utilization — subprocesses run in parallel across cores")
    print(f"  - If OS runs out of memory/PIDs, subprocess spawning will fail")
    print()


# ---------------------------------------------------------------------------
# Standalone monitor mode — watch subprocesses without triggering calls
# ---------------------------------------------------------------------------
async def run_monitor(server_pid: int, duration: int = 120, server_url: str = "http://localhost:7860") -> None:
    """Continuously monitor the Pipecat server and its bot subprocesses.

    Run this in a separate terminal while manually triggering calls
    to watch subprocesses spawn and die in real time.
    Uses both psutil and the /calls API endpoint.
    """
    print(f"\n  Monitoring server PID {server_pid} and bot subprocesses for {duration}s")
    print(f"  (Trigger calls manually or from another terminal)")
    print(f"  Subprocesses identified by: {BOT_WORKER_PATTERN}")
    print(f"  API endpoint: {server_url}/calls\n")
    print(f"  {'Time':>8}  {'SvrCPU':>7}  {'SvrMEM':>9}  {'Conns':>6}  |  "
          f"{'BotProcs':>8}  {'APICalls':>8}  {'BotCPU':>7}  {'BotMEM':>9}")
    print(f"  {'─' * 8}  {'─' * 7}  {'─' * 9}  {'─' * 6}  |  "
          f"{'─' * 8}  {'─' * 8}  {'─' * 7}  {'─' * 9}")

    elapsed = 0
    while elapsed < duration:
        snap = await take_server_snapshot(server_pid, server_url)
        if not snap:
            break
        print(
            f"  {snap.timestamp:>8}  {snap.server_cpu_percent:>6.1f}%  "
            f"{snap.server_memory_mb:>7.1f}MB  {snap.server_connections:>6}  |  "
            f"{snap.bot_subprocess_count:>8}  {snap.api_call_count:>8}  {snap.total_bot_cpu:>6.1f}%  "
            f"{snap.total_bot_memory_mb:>7.1f}MB"
        )

        # Show per-process details every 10 seconds
        if elapsed % 10 == 0 and (snap.bot_processes or snap.api_calls):
            print_subprocess_details(snap)

        await asyncio.sleep(2)
        elapsed += 2

    # Final ps aux dump
    print(f"\n  Final ps aux snapshot:")
    ps_output = run_ps_aux_grep()
    if ps_output:
        for line in ps_output.split("\n"):
            print(f"    {line}")
    else:
        print("    (no bot_worker subprocesses running)")

    # Final /calls check
    api_calls = await fetch_active_calls(server_url)
    print(f"\n  Final /calls API: {len(api_calls)} active calls")
    for c in api_calls:
        print(f"    pid={c.pid} agent_id={c.agent_id} call_sid={c.call_sid} alive={c.alive}")
    print()


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
def _print_summary(
    results: list[CallResult],
    final_statuses: dict[str, str],
    server_pid: Optional[int],
    server_url: str = "http://localhost:7860",
) -> None:
    succeeded = sum(1 for r in results if r.status != "failed")
    failed = len(results) - succeeded
    avg_latency = sum(r.api_latency_ms for r in results) / len(results) if results else 0

    # Check remaining subprocesses
    remaining_procs = find_bot_worker_processes()

    print(f"\n{'=' * 80}")
    print(f"  Call Results (Subprocess-per-Call Model)")
    print(f"{'=' * 80}")
    print(f"  Total: {len(results)}  Succeeded: {succeeded}  Failed: {failed}")
    print(f"  Avg Twilio API latency: {avg_latency:.0f}ms")
    print(f"  Remaining bot subprocesses: {len(remaining_procs)} (psutil)")

    if final_statuses:
        status_counts: dict[str, int] = {}
        for status in final_statuses.values():
            status_counts[status] = status_counts.get(status, 0) + 1
        print(f"\n  Final call statuses:")
        for status, count in sorted(status_counts.items()):
            print(f"    {status}: {count}")

    if failed > 0:
        print(f"\n  Failed calls:")
        for r in results:
            if r.status == "failed":
                print(f"    #{r.call_index}: {r.error}")

    print(f"\n  How Pipecat handled these calls:")
    print(f"    - Each call -> WebSocket to /ws -> SubprocessBotManager.spawn_bot()")
    print(f"    - Each call ran in its OWN subprocess (core.bot_worker)")
    print(f"    - Verify with: ps aux | grep {BOT_WORKER_PATTERN}")
    print(f"    - Or query: curl {server_url}/calls")
    print(f"    - /status endpoint receives Twilio callbacks -> handle_call_status() -> subprocess cleanup")
    print(f"    - Server process just proxied WebSocket <-> subprocess stdin/stdout")
    if server_pid:
        print(f"    - Check server metrics above to see resource usage breakdown")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load test for Pipecat voice agents (subprocess-per-call model via SubprocessBotManager)"
    )
    parser.add_argument(
        "--mode",
        choices=["calls", "load_test", "monitor"],
        default="calls",
        help="'calls' = fire N calls, 'load_test' = gradual ramp-up, 'monitor' = watch subprocesses only",
    )
    parser.add_argument("--calls", type=int, default=5, help="Number of concurrent calls (default: 5)")
    parser.add_argument("--delay", type=float, default=0.0, help="Delay between calls in seconds")
    parser.add_argument("--duration", type=int, default=30, help="How long to monitor active calls in seconds")
    parser.add_argument("--from-number", default=None, help="Twilio number (E.164). Falls back to env var")
    parser.add_argument("--to-number", default=None, help="Target phone number (E.164)")
    parser.add_argument("--webhook-url", default=None, help="Backend webhook URL (e.g. https://example.com/voice)")
    parser.add_argument("--server-pid", type=int, default=None, help="PID of running Pipecat server (auto-detected if omitted)")
    parser.add_argument("--server-url", default="http://localhost:7860", help="Base URL for /calls and /status endpoints (default: http://localhost:7860)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.mode == "monitor":
        pid = args.server_pid or find_server_pid()
        if not pid:
            logger.error("Could not find server process. Use --server-pid")
            sys.exit(1)
        asyncio.run(run_monitor(pid, args.duration, args.server_url))
        return

    # Calls and load_test modes require these
    if not args.to_number or not args.webhook_url:
        logger.error("--to-number and --webhook-url are required for %s mode", args.mode)
        sys.exit(1)

    config = CallConfig(
        from_number=args.from_number or default_from_number(),
        to_number=args.to_number,
        webhook_url=args.webhook_url,
        num_calls=args.calls,
        delay=args.delay,
        call_duration=args.duration,
        server_pid=args.server_pid,
        server_url=args.server_url,
    )

    if args.mode == "calls":
        asyncio.run(run_concurrent_calls(config))
    elif args.mode == "load_test":
        asyncio.run(run_load_test(config))


if __name__ == "__main__":
    main()
