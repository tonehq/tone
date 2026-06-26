from typing import Dict, List, Type

from core.services.webrtc.provider import WebRTCProvider

_PROVIDERS: Dict[str, Type[WebRTCProvider]] = {}


def register_provider(channel_type: str, provider_cls: Type[WebRTCProvider]) -> None:
    _PROVIDERS[channel_type] = provider_cls


def build_provider(channel_type: str, config: dict) -> WebRTCProvider:
    provider_cls = _PROVIDERS.get(channel_type)
    if provider_cls is None:
        raise ValueError(f"Unsupported web channel: {channel_type}")
    return provider_cls.from_config(config)


def supported_providers() -> List[str]:
    return list(_PROVIDERS)
