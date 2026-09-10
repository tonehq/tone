import pytest
from pydantic import ValidationError

from core.api.v1.outbound_calls import CreateOutboundCallRequest
from core.services.outbound_call_service import (
    PSTN_TRIGGER_PROVIDERS,
    SUPPORTED_TRIGGER_PROVIDERS,
    OutboundCallService,
    TriggerProvider,
)

AGENT_ID = "f8e20d72-4799-4094-b7dc-4d49f45c8f98"


@pytest.mark.parametrize("provider", SUPPORTED_TRIGGER_PROVIDERS)
def test_request_accepts_every_trigger_provider_the_service_supports(provider):
    parsed = CreateOutboundCallRequest(agent_id=AGENT_ID, provider=provider).provider
    assert parsed == provider and parsed.value == provider
    assert provider in OutboundCallService._SUPPORTED_PROVIDERS


def test_provider_tuples_follow_the_enum():
    assert set(SUPPORTED_TRIGGER_PROVIDERS) == {provider.value for provider in TriggerProvider}
    assert set(PSTN_TRIGGER_PROVIDERS) == set(SUPPORTED_TRIGGER_PROVIDERS) - {TriggerProvider.WEBSOCKET.value}


def test_request_rejects_an_unknown_provider():
    with pytest.raises(ValidationError):
        CreateOutboundCallRequest(agent_id=AGENT_ID, provider="carrier-pigeon")
