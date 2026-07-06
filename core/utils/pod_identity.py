import os
from functools import lru_cache
from typing import Dict, Optional

_POD_NAME_ENV = "POD_NAME"
_NODE_NAME_ENV = "NODE_NAME"
_DEPLOYMENT_NAME_ENV = "DEPLOYMENT_NAME"
_ENVIRONMENT_ENV = "ENV"


def pod_name() -> Optional[str]:
    return os.environ.get(_POD_NAME_ENV) or None


def node_name() -> Optional[str]:
    return os.environ.get(_NODE_NAME_ENV) or None


def deployment_name() -> Optional[str]:
    return os.environ.get(_DEPLOYMENT_NAME_ENV) or None


def environment() -> Optional[str]:
    return os.environ.get(_ENVIRONMENT_ENV) or None


@lru_cache(maxsize=1)
def get_served_by() -> Dict[str, str]:
    served_by: Dict[str, str] = {}
    dep = deployment_name()
    pod = pod_name()
    node = node_name()
    env = environment()
    if dep:
        served_by["deployment"] = dep
    if pod:
        served_by["pod"] = pod
    if node:
        served_by["node"] = node
    if env:
        served_by["environment"] = env
    return served_by


def parse_ordinal(pod: Optional[str], deployment: Optional[str]) -> Optional[int]:
    if not pod or not deployment:
        return None
    prefix = deployment + "-"
    if pod.startswith(prefix):
        suffix = pod[len(prefix):]
        if suffix.isdigit():
            return int(suffix)
    return None
