from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import core.api.telephony_routes as routes
from core.services.outbound_call_service import _TWILIO_STATUS_MAP, OutboundCallService


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(routes, "fallback_media_ws_url", lambda hostname: "wss://call.example/ws")
    monkeypatch.setattr(routes, "pinned_ws_url", lambda default, tag: (default, "pod-0", 0, "node-a"))
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app)


def _ws_query(uri):
    parsed = urlparse(uri)
    assert parsed.scheme == "wss" and parsed.path == "/ws"
    return parse_qs(parsed.query)


def test_plivo_inbound_answer_streams_with_from_and_to(client):
    response = client.post("/plivo/answer", data={"From": "+15550001111", "To": "+15550002222", "CallUUID": "c1"})
    assert response.status_code == 200 and response.headers["content-type"].startswith("application/xml")
    stream = ElementTree.fromstring(response.text).find("Stream")
    assert stream.attrib["bidirectional"] == "true"
    assert _ws_query(stream.text) == {"from": ["+15550001111"], "to": ["+15550002222"]}


def test_plivo_inbound_answer_normalises_bare_digit_numbers(client):
    response = client.post("/plivo/answer", data={"From": "917981332723", "To": "13474282218", "CallUUID": "c1"})
    stream = ElementTree.fromstring(response.text).find("Stream")
    assert _ws_query(stream.text) == {"from": ["+917981332723"], "to": ["+13474282218"]}


def test_plivo_outbound_answer_carries_agent_and_direction(client):
    response = client.post("/plivo/outbound?agent_id=a1&from=%2B1&to=%2B2&scheduled_call_id=sc1")
    stream = ElementTree.fromstring(response.text).find("Stream")
    assert _ws_query(stream.text) == {
        "from": ["+1"], "to": ["+2"], "agent_id": ["a1"], "direction": ["outbound"], "scheduled_call_id": ["sc1"],
    }


def test_plivo_outbound_answer_without_agent_hangs_up(client):
    response = client.post("/plivo/outbound")
    assert "<Hangup/>" in response.text


def test_vonage_inbound_answer_returns_ncco_with_e164_numbers(client):
    response = client.get("/vonage/answer?from=15550001111&to=15550002222&uuid=u-1&conversation_uuid=cv-1")
    assert response.status_code == 200 and response.headers["content-type"].startswith("application/json")
    endpoint = response.json()[0]["endpoint"][0]
    assert endpoint["type"] == "websocket" and endpoint["content-type"] == "audio/l16;rate=16000"
    assert _ws_query(endpoint["uri"]) == {
        "provider": ["vonage"], "from": ["+15550001111"], "to": ["+15550002222"], "call_id": ["u-1"],
    }


def test_vonage_outbound_answer_uses_the_dial_params(client):
    response = client.get("/vonage/answer?agent_id=a1&direction=outbound&from=%2B1&to=%2B2&uuid=u-2")
    query = _ws_query(response.json()[0]["endpoint"][0]["uri"])
    assert query["agent_id"] == ["a1"] and query["direction"] == ["outbound"] and query["call_id"] == ["u-2"]
    assert query["provider"] == ["vonage"]


def test_status_callbacks_without_scheduled_id_ack_and_skip_the_db(client, monkeypatch):
    monkeypatch.setattr(routes, "get_db_context", lambda: (_ for _ in ()).throw(AssertionError("db touched")))
    assert client.post("/plivo/outbound-status", data={"CallUUID": "c1", "CallStatus": "completed"}).status_code == 204
    assert client.post("/vonage/events", json={"uuid": "u1", "status": "completed"}).status_code == 204


def test_status_callbacks_map_provider_fields_onto_the_shared_handler(client, monkeypatch):
    seen = []

    class _Session:
        def query(self, model):
            return self

        def filter(self, *args):
            return self

        def first(self):
            return type("Row", (), {"organization_id": "org-1"})()

    class _Ctx:
        def __enter__(self):
            return _Session()

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(routes, "get_db_context", lambda: _Ctx())
    monkeypatch.setattr(OutboundCallService, "__init__", lambda self, db, org_id=None: None)
    monkeypatch.setattr(
        OutboundCallService, "handle_status_callback", lambda self, sid, form: seen.append((sid, form)),
    )
    client.post(
        "/plivo/outbound-status?scheduled_call_id=sc1",
        data={
            "RequestUUID": "req-1", "CallUUID": "c1", "CallStatus": "no-answer",
            "Duration": "0", "To": "2", "From": "+1",
        },
    )
    assert seen[0] == (
        "sc1", {"CallSid": "req-1", "CallStatus": "no-answer", "CallDuration": "0", "To": "+2", "From": "+1"},
    )
    client.post(
        "/vonage/events?scheduled_call_id=sc2",
        json={"uuid": "u1", "status": "unanswered", "duration": "0", "to": "2", "from": "1"},
    )
    assert seen[1] == (
        "sc2", {"CallSid": "u1", "CallStatus": "unanswered", "CallDuration": "0", "To": "+2", "From": "+1"},
    )


def test_provider_statuses_are_mapped_onto_the_scheduled_call_states():
    assert _TWILIO_STATUS_MAP["cancel"] == "canceled"
    assert _TWILIO_STATUS_MAP["unanswered"] == "no_answer"
    assert _TWILIO_STATUS_MAP["answered"] == "in_progress"
    assert _TWILIO_STATUS_MAP["rejected"] == "failed"
    assert set(OutboundCallService._PSTN_PROVIDERS) >= {"plivo", "vonage"}
    assert set(OutboundCallService._SUPPORTED_PROVIDERS) >= {"plivo", "vonage"}
