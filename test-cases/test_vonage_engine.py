import json
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from core.services.call_engines import VonageCallEngine, get_call_engine, vonage_engine


def _response(status_code=200, payload=None, text=""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload if payload is not None else {}
    resp.text = text
    resp.raise_for_status.return_value = None
    return resp


@pytest.fixture
def vonage_key():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption(),
    ).decode()
    public = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return pem, public


@pytest.fixture
def vonage_creds(monkeypatch, vonage_key):
    pem, _ = vonage_key
    monkeypatch.setattr(
        vonage_engine, "get_vonage_credentials",
        lambda org_id=None: {"application_id": "app-1", "private_key": pem, "api_key": "k", "api_secret": "s"},
    )


class TestFactory:
    def test_returns_the_vonage_engine(self):
        assert isinstance(get_call_engine("vonage", org_id="org-1"), VonageCallEngine)
        assert get_call_engine("vonage").provider_name == "vonage"

    def test_answer_document_is_json(self):
        assert get_call_engine("vonage").answer_media_type == "application/json"
        assert json.loads(get_call_engine("vonage").hangup_answer) == []


class TestVonageNcco:
    def test_connect_ncco_carries_provider_and_params(self):
        raw = get_call_engine("vonage").generate_twiml(
            "wss://pod-1.example/ws",
            {"agent_id": "a1", "direction": "outbound", "from": "+15", "to": "", "call_id": "u-1"},
        )
        ncco = json.loads(raw)
        endpoint = ncco[0]["endpoint"][0]
        assert ncco[0]["action"] == "connect"
        assert endpoint["type"] == "websocket" and endpoint["content-type"] == "audio/l16;rate=16000"
        assert parse_qs(urlparse(endpoint["uri"]).query) == {
            "provider": ["vonage"], "agent_id": ["a1"], "direction": ["outbound"], "from": ["+15"], "call_id": ["u-1"],
        }

    def test_bare_digit_numbers_are_normalised_to_e164(self):
        raw = get_call_engine("vonage").generate_twiml(
            "wss://pod-1.example/ws", {"from": "917981332723", "to": "15550002222", "call_id": "u-1"},
        )
        query = parse_qs(urlparse(json.loads(raw)[0]["endpoint"][0]["uri"]).query)
        assert query["from"] == ["+917981332723"] and query["to"] == ["+15550002222"]


class TestVonageInitiateAndEnd:
    def test_initiate_signs_a_jwt_and_returns_the_call_uuid(self, vonage_creds, vonage_key):
        _, public = vonage_key
        created = _response(201, {"uuid": "call-1", "status": "started"})
        with patch.object(vonage_engine.requests, "post", return_value=created) as post:
            info = VonageCallEngine(org_id="org-1").initiate_call(
                to_number="+15550002222", from_number="+15550001111", agent_id="agent-1",
                callback_base_url="https://call.example", scheduled_call_id="sc-1",
            )
        assert info.call_id == "call-1" and info.provider == "vonage" and info.status == "queued"
        url, kwargs = post.call_args[0][0], post.call_args[1]
        assert url == "https://api.nexmo.com/v1/calls"
        token = kwargs["headers"]["Authorization"].split(" ", 1)[1]
        claims = jwt.decode(token, public, algorithms=["RS256"])
        assert claims["application_id"] == "app-1" and claims["jti"] and claims["exp"] > claims["iat"]
        payload = kwargs["json"]
        assert payload["to"] == [{"type": "phone", "number": "15550002222"}]
        assert payload["from"] == {"type": "phone", "number": "15550001111"}
        assert parse_qs(urlparse(payload["answer_url"][0]).query)["agent_id"] == ["agent-1"]
        assert payload["event_url"] == ["https://call.example/vonage/events?scheduled_call_id=sc-1"]

    def test_initiate_requires_a_callback_base(self, vonage_creds):
        with pytest.raises(ValueError, match="BASE_CALL_URL"):
            VonageCallEngine().initiate_call("+1", "+2", "a", "")

    def test_end_call_puts_hangup(self, vonage_creds):
        with patch.object(vonage_engine.requests, "put", return_value=_response(204)) as put:
            assert VonageCallEngine().end_call("call-1") is True
        assert put.call_args[0][0] == "https://api.nexmo.com/v1/calls/call-1"
        assert put.call_args[1]["json"] == {"action": "hangup"}

    def test_end_call_accepts_already_completed(self, vonage_creds):
        with patch.object(vonage_engine.requests, "put", return_value=_response(400)), \
                patch.object(vonage_engine.requests, "get", return_value=_response(200, {"status": "completed"})):
            assert VonageCallEngine().end_call("call-1") is True

    def test_transfer_builds_phone_or_sip_endpoints(self, vonage_creds):
        with patch.object(vonage_engine.requests, "put", return_value=_response(204)) as put:
            assert VonageCallEngine().transfer_call("call-1", "+1 555 0100") is True
            assert VonageCallEngine().transfer_call(
                "call-1", "sip:agent@pbx.example", headers={"X-Reason": "vip"},
            ) is True
        phone, sip_ = [c[1]["json"]["destination"]["ncco"][0]["endpoint"][0] for c in put.call_args_list]
        assert phone == {"type": "phone", "number": "15550100"}
        assert sip_ == {"type": "sip", "uri": "sip:agent@pbx.example", "headers": {"X-Reason": "vip"}}

    def test_get_call_status_maps_vonage_states(self, vonage_creds):
        detail = _response(200, {"status": "unanswered", "duration": "0", "price": "0.0"})
        with patch.object(vonage_engine.requests, "get", return_value=detail):
            assert VonageCallEngine().get_call_status("call-1")["status"] == "no-answer"

    def test_missing_credentials_raise(self, monkeypatch):
        monkeypatch.setattr(vonage_engine, "get_vonage_credentials", lambda org_id=None: {})
        with pytest.raises(ValueError, match="Vonage channel"):
            VonageCallEngine().initiate_call("+1", "+2", "a", "https://call.example")
