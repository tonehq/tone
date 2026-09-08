"""Unit test for the Twilio telephony transport.

Source: core/services/transport/twilio.py::TwilioTransport.create_serializer.
The serializer keeps auto_hang_up ENABLED so it drops the line promptly during
the EndFrame (before teardown/recording upload), using credentials resolved for
the call's org (call_data["_org_id"], set in TelephonyTransport.build).
"""

import core.services.transport.twilio as twilio_mod
from core.services.transport.twilio import TwilioTransport


def test_twilio_serializer_enables_prompt_hangup(monkeypatch):
    captured = {}

    def _fake_creds(org_id=None):
        captured["org_id"] = org_id
        return {"account_sid": "AC", "auth_token": "tok"}

    monkeypatch.setattr(twilio_mod, "get_twilio_credentials", _fake_creds)
    serializer = TwilioTransport().create_serializer(
        {"stream_id": "MZ1", "call_id": "CA1", "_org_id": "org-123"}
    )
    # Prompt hangup during EndFrame stays on.
    assert serializer._params.auto_hang_up is True
    # Credentials are looked up for the call's org, not org_id=None.
    assert captured["org_id"] == "org-123"
