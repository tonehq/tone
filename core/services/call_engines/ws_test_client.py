"""Client for the remote tone-test WS-bridge test-run API.

Before fanning out WebSocket-bridge calls, havana asks the remote deployment (the same one whose
``/ws/test`` the bridge dials) to PREPARE a tracked test run for the dialed number: the remote resolves
the agent, creates one ``TestRun`` + N pending scenario mappings over that agent's cases, and returns
``{run_id, scenarios:[{scenario_id, name}]}``. havana then dials ``/ws/test`` once per scenario, so each
case runs its own persona and is recorded — appearing in the remote's Test Runs UI.

The HTTP base is derived from ``WS_CALL_TARGET_URL`` (ws→http, wss→https); the endpoint is
unauthenticated + org-agnostic (the dialed number carries its own org on the remote).
"""

from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from shared.config import settings

_PREPARE_TIMEOUT_SECONDS = 10.0


def _http_base() -> Optional[str]:
    """Derive the remote HTTP base from ``WS_CALL_TARGET_URL`` (ws→http, wss→https)."""
    target = (settings.WS_CALL_TARGET_URL or "").strip().rstrip("/")
    if not target:
        return None
    if target.startswith("wss://"):
        return "https://" + target[len("wss://"):]
    if target.startswith("ws://"):
        return "http://" + target[len("ws://"):]
    return target


def prepare_bridge_run(to_number: str) -> Optional[Dict[str, Any]]:
    """Ask the remote to prepare a tracked test run for ``to_number``.

    Returns ``{run_id, agent_id, scenarios:[{scenario_id, name, execution_order}]}`` on success, or
    ``None`` when the number maps to no agent/scenarios (404) or the remote is unreachable — the caller
    then falls back to an untracked bridge fan-out. Never raises."""
    base = _http_base()
    if not base:
        return None
    url = f"{base}/api/v1/ws-test/prepare"
    try:
        resp = httpx.post(
            url, json={"phone_number": (to_number or "").strip()}, timeout=_PREPARE_TIMEOUT_SECONDS
        )
    except httpx.HTTPError as exc:
        logger.warning("[outbound][ws] prepare call to {} failed: {}", url, exc)
        return None
    if resp.status_code == 404:
        logger.info("[outbound][ws] no tracked scenarios for {} (remote 404) — untracked fan-out", to_number)
        return None
    if resp.status_code >= 400:
        logger.warning("[outbound][ws] prepare returned {} for {}", resp.status_code, to_number)
        return None
    try:
        data = resp.json() or {}
    except ValueError as exc:
        # 2xx with a non-JSON body (e.g. an HTML error page from a proxy/LB). Honor the
        # "Never raises" contract so the caller falls back to an untracked fan-out.
        logger.warning("[outbound][ws] prepare returned non-JSON body for {}: {}", to_number, exc)
        return None
    scenarios: List[Dict[str, Any]] = data.get("scenarios") or []
    if not data.get("run_id") or not scenarios:
        return None
    return data
