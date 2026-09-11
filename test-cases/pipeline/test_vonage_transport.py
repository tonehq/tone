from core.services.transport.registry import get_telephony_provider
from core.services.transport.vonage import VONAGE_SAMPLE_RATE, VonageTransport


def test_registry_offers_vonage():
    assert isinstance(get_telephony_provider("vonage"), VonageTransport)


def test_vonage_serializer_defaults_to_16k_and_honours_call_sample_rate():
    default = VonageTransport().create_serializer({"call_id": "u1", "stream_id": "u1"})
    assert default._params.vonage_sample_rate == VONAGE_SAMPLE_RATE == 16000
    custom = VonageTransport().create_serializer({"call_id": "u1", "stream_id": "u1", "sample_rate": "8000"})
    assert custom._params.vonage_sample_rate == 8000
