import time
from typing import Optional, Tuple

_CGROUP = "/sys/fs/cgroup"


def _read(path: str) -> Optional[str]:
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return None


def memory_usage() -> Tuple[Optional[float], Optional[float]]:
    used = _read(f"{_CGROUP}/memory.current")
    limit = _read(f"{_CGROUP}/memory.max")
    used_mb = float(used) / (1024 * 1024) if used and used.isdigit() else None
    limit_mb = float(limit) / (1024 * 1024) if limit and limit.isdigit() else None
    return used_mb, limit_mb


def _cpu_usage_usec() -> Optional[int]:
    data = _read(f"{_CGROUP}/cpu.stat")
    if not data:
        return None
    for line in data.splitlines():
        if line.startswith("usage_usec"):
            try:
                return int(line.split()[1])
            except (ValueError, IndexError):
                return None
    return None

def _cpu_limit_cores() -> Optional[float]:
    data = _read(f"{_CGROUP}/cpu.max")
    if not data:
        return None
    parts = data.split()
    if not parts or parts[0] == "max":
        return None
    try:
        quota = int(parts[0])
        period = int(parts[1]) if len(parts) > 1 else 100000
        return quota / period if period else None
    except (ValueError, IndexError):
        return None


def cpu_usage(interval: float = 0.3) -> Tuple[Optional[float], Optional[float]]:
    limit = _cpu_limit_cores()
    start = _cpu_usage_usec()
    if start is None:
        return None, limit
    time.sleep(interval)
    end = _cpu_usage_usec()
    if end is None:
        return None, limit
    used_cores = (end - start) / (interval * 1_000_000)
    return used_cores, limit
