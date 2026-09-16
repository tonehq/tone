"""App node-pool strategy factory — dispatch by Kubernetes provider."""

from .azure import AzureAgentPool
from .base import AppNodePool
from .digitalocean import DoNodePool

_STRATEGIES = {
    "azure": AzureAgentPool,
    "digitalocean": DoNodePool,
}


def create_app_pool(provider, name, cfg, opts):
    strategy = _STRATEGIES.get(provider)
    if strategy is None:
        raise Exception(
            f"app node pool provider '{provider}' is not implemented "
            f"(expected one of: {sorted(_STRATEGIES)})"
        )
    return strategy(name, cfg).create(opts)


__all__ = ["create_app_pool", "AppNodePool"]
