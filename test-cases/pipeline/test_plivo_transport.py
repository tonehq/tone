import asyncio

import core.services.transport.plivo as plivo_mod
from core.services.transport.plivo import PlivoTransport
from core.services.transport.registry import get_telephony_provider


def test_registry_offers_plivo():
    assert isinstance(get_telephony_provider("plivo"), PlivoTransport)


def test_plivo_serializer_uses_the_call_org_credentials(monkeypatch):
    captured = {}

    def _creds(org_id=None):
        captured["org_id"] = org_id
        return {"auth_id": "MA1", "auth_token": "tok"}

    monkeypatch.setattr(plivo_mod, "get_plivo_credentials", _creds)
    serializer = PlivoTransport().create_serializer({"stream_id": "S1", "call_id": "C1", "_org_id": "org-9"})
    assert captured["org_id"] == "org-9"
    assert serializer._auth_id == "MA1" and serializer._auth_token == "tok"
    assert serializer._params.auto_hang_up is True


def test_plivo_resolve_from_to_falls_back_to_the_live_call_lookup(monkeypatch):
    calls = []

    async def _lookup(call_uuid, org_id=None):
        calls.append((call_uuid, org_id))
        return {"from_number": "+15550001111", "to_number": "+15550002222"}

    monkeypatch.setattr(plivo_mod, "get_plivo_call_info", _lookup)
    call_data = {"stream_id": "S1", "call_id": "C1", "_org_id": "org-9"}
    asyncio.run(PlivoTransport().resolve_from_to(call_data))
    assert call_data["from"] == "+15550001111" and call_data["to"] == "+15550002222"
    assert calls == [("C1", "org-9")]
    known = {"stream_id": "S1", "call_id": "C1", "from": "+1", "to": "+2"}
    asyncio.run(PlivoTransport().resolve_from_to(known))
    assert len(calls) == 1
