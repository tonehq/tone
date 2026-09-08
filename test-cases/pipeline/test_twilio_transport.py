"""Unit test for the Twilio telephony transport.

Source: core/services/transport/twilio.py::TwilioTransport.create_serializer.
The serializer must be built with auto_hang_up DISABLED — the provider-agnostic
terminator (core/services/call_termination) owns the REST hangup for Twilio with
the correct per-call org creds, so the serializer must not also fire an org-less
(401) hangup.
"""

from core.services.transport.twilio import TwilioTransport


def test_twilio_serializer_disables_auto_hang_up():
    serializer = TwilioTransport().create_serializer({"stream_id": "MZ1", "call_id": "CA1"})
    assert serializer._params.auto_hang_up is False
