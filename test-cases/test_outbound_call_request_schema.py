import pytest
from pydantic import ValidationError

from core.api.v1.outbound_calls import CreateOutboundCallRequest
from core.services.outbound_call_service import SUPPORTED_TRIGGER_PROVIDERS, OutboundCallService

AGENT_ID = "f8e20d72-4799-4094-b7dc-4d49f45c8f98"


@pytest.mark.parametrize("provider", SUPPORTED_TRIGGER_PROVIDERS)
def test_request_accepts_every_trigger_provider_the_service_supports(provider):
    assert CreateOutboundCallRequest(agent_id=AGENT_ID, provider=provider).provider == provider
    assert provider in OutboundCallService._SUPPORTED_PROVIDERS


def test_request_rejects_an_unknown_provider():
    with pytest.raises(ValidationError):
        CreateOutboundCallRequest(agent_id=AGENT_ID, provider="carrier-pigeon")
