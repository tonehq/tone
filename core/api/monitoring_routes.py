from threading import Lock

from fastapi import APIRouter
from fastapi.responses import Response

from core.utils.pod_identity import get_served_by, pod_name, node_name, deployment_name
from core.utils.pod_resources import memory_usage, cpu_usage

router = APIRouter()

_active_calls_lock = Lock()
_active_calls = 0
_draining = False


def active_calls_inc() -> None:
    global _active_calls
    with _active_calls_lock:
        _active_calls += 1


def active_calls_dec() -> None:
    global _active_calls
    with _active_calls_lock:
        if _active_calls > 0:
            _active_calls -= 1


def active_calls_count() -> int:
    with _active_calls_lock:
        return _active_calls


def set_draining(value: bool = True) -> None:
    global _draining
    _draining = value


def is_draining() -> bool:
    return _draining


def _pod_labels() -> str:
    parts = []
    if pod_name():
        parts.append(f'pod="{pod_name()}"')
    if node_name():
        parts.append(f'node="{node_name()}"')
    if deployment_name():
        parts.append(f'deployment="{deployment_name()}"')
    return "{" + ",".join(parts) + "}" if parts else ""


@router.get("/status")
def status():
    with _active_calls_lock:
        active = _active_calls
    mem_used_mb, mem_limit_mb = memory_usage()
    cpu_used_cores, cpu_limit_cores = cpu_usage()
    return {
        "served_by": get_served_by() or None,
        "active_calls": active,
        "mem_used_mb": mem_used_mb,
        "mem_limit_mb": mem_limit_mb,
        "cpu_used_cores": cpu_used_cores,
        "cpu_limit_cores": cpu_limit_cores,
    }


@router.post("/drain")
@router.get("/drain")
def drain():
    set_draining(True)
    return {"draining": True, "active_calls": active_calls_count()}


@router.get("/metrics")
def metrics():
    with _active_calls_lock:
        active = _active_calls
    labels = _pod_labels()
    body = (
        "# HELP tone_active_calls Active call WebSocket connections on this pod\n"
        "# TYPE tone_active_calls gauge\n"
        f"tone_active_calls{labels} {active}\n"
    )
    return Response(content=body, media_type="text/plain; version=0.0.4")
