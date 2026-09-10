from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree

import pytest

from core.services.call_engines import PlivoCallEngine, get_call_engine, plivo_engine
from core.services.call_engines.base import CallEngine


def _response(status_code=200, payload=None, text=""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload if payload is not None else {}
    resp.text = text
    resp.raise_for_status.return_value = None
    return resp


@pytest.fixture
def plivo_creds(monkeypatch):
    monkeypatch.setattr(
        plivo_engine, "get_plivo_credentials", lambda org_id=None: {"auth_id": "MA123", "auth_token": "tok"},
    )


class TestFactory:
    def test_returns_provider_engines(self):
        assert isinstance(get_call_engine("plivo", org_id="org-1"), PlivoCallEngine)
        assert isinstance(get_call_engine("plivo"), CallEngine)
        assert get_call_engine("plivo").provider_name == "plivo"

    def test_answer_documents_declare_their_media_type(self):
        assert get_call_engine("plivo").answer_media_type == "application/xml"
        assert "<Hangup/>" in get_call_engine("plivo").hangup_answer


class TestPlivoAnswerXml:
    def test_stream_points_at_ws_with_params_on_the_query_string(self):
        xml = get_call_engine("plivo").generate_twiml(
            "wss://pod-1.example/ws", {"agent_id": "a1", "direction": "outbound", "from": "15550001111", "to": ""},
        )
        root = ElementTree.fromstring(xml)
        stream = root.find("Stream")
        assert stream.attrib == {
            "bidirectional": "true", "keepCallAlive": "true", "contentType": "audio/x-mulaw;rate=8000",
        }
        parsed = urlparse(stream.text)
        assert parsed.scheme == "wss" and parsed.path == "/ws"
        query = parse_qs(parsed.query)
        assert query == {"agent_id": ["a1"], "direction": ["outbound"], "from": ["+15550001111"]}


class TestPlivoInitiateAndEnd:
    def test_initiate_posts_the_answer_url_and_returns_the_request_uuid(self, plivo_creds):
        created = _response(201, {"request_uuid": "req-9"})
        with patch.object(plivo_engine.requests, "post", return_value=created) as post:
            info = PlivoCallEngine(org_id="org-1").initiate_call(
                to_number="+15550002222", from_number="+15550001111", agent_id="agent-1",
                callback_base_url="https://call.example/", scheduled_call_id="sc-1",
            )
        assert info.call_id == "req-9" and info.provider == "plivo" and info.status == "queued"
        url, kwargs = post.call_args[0][0], post.call_args[1]
        assert url == "https://api.plivo.com/v1/Account/MA123/Call/"
        assert kwargs["auth"] == ("MA123", "tok")
        payload = kwargs["json"]
        assert payload["from"] == "15550001111" and payload["to"] == "15550002222"
        answer = urlparse(payload["answer_url"])
        assert answer.path == "/plivo/outbound"
        assert parse_qs(answer.query)["scheduled_call_id"] == ["sc-1"]
        assert payload["hangup_url"] == "https://call.example/plivo/outbound-status?scheduled_call_id=sc-1"

    def test_initiate_requires_a_callback_base(self, plivo_creds):
        with pytest.raises(ValueError, match="BASE_CALL_URL"):
            PlivoCallEngine().initiate_call("+1", "+2", "a", "")

    def test_end_call_hangs_up_live_call_then_falls_back_to_request_cancel(self, plivo_creds):
        with patch.object(plivo_engine.requests, "delete", side_effect=[_response(404), _response(204)]) as delete:
            assert PlivoCallEngine().end_call("req-9") is True
        assert [c[0][0] for c in delete.call_args_list] == [
            "https://api.plivo.com/v1/Account/MA123/Call/req-9/",
            "https://api.plivo.com/v1/Account/MA123/Request/req-9/",
        ]

    def test_end_call_treats_terminal_status_as_success(self, plivo_creds):
        with patch.object(plivo_engine.requests, "delete", return_value=_response(404)), \
                patch.object(plivo_engine.requests, "get", return_value=_response(200, {"call_status": "completed"})):
            assert PlivoCallEngine().end_call("uuid-1") is True

    def test_get_call_status_reads_the_live_call(self, plivo_creds):
        live = _response(200, {"call_status": "in-progress", "call_duration": 12})
        with patch.object(plivo_engine.requests, "get", return_value=live):
            status = PlivoCallEngine().get_call_status("uuid-1")
        assert status == {"status": "in-progress", "duration": 12, "price": None, "answered_by": None}

    @pytest.mark.parametrize(
        ("record", "expected"),
        [
            ({"answer_time": "2026-09-10 08:45:15+00:00", "hangup_cause_name": "Normal Hangup"}, "completed"),
            ({"answer_time": "2026-09-10 08:45:15+00:00", "hangup_cause_name": "Network Error"}, "completed"),
            ({"answer_time": None, "hangup_cause_name": "Busy Line"}, "busy"),
            ({"answer_time": None, "hangup_cause_name": "Ring Timeout Reached"}, "no-answer"),
            ({"answer_time": None, "hangup_cause_name": "Canceled"}, "canceled"),
            ({"answer_time": None, "hangup_cause_name": "Unallocated number"}, "failed"),
        ],
    )
    def test_get_call_status_derives_a_finished_call_from_its_record(self, plivo_creds, record, expected):
        responses = [_response(404), _response(200, {**record, "bill_duration": 7, "total_amount": "0.01"})]
        with patch.object(plivo_engine.requests, "get", side_effect=responses):
            status = PlivoCallEngine().get_call_status("uuid-1")
        assert status == {"status": expected, "duration": 7, "price": "0.01", "answered_by": None}

    def test_end_call_confirms_a_finished_call_through_its_record(self, plivo_creds):
        record = _response(200, {"call_state": "ANSWER", "answer_time": "2026-09-10 08:45:15+00:00"})
        with patch.object(plivo_engine.requests, "delete", return_value=_response(404)), \
                patch.object(plivo_engine.requests, "get", side_effect=[_response(404), record]):
            assert PlivoCallEngine().end_call("uuid-1") is True

    def test_missing_credentials_raise(self, monkeypatch):
        monkeypatch.setattr(plivo_engine, "get_plivo_credentials", lambda org_id=None: {})
        with pytest.raises(ValueError, match="Plivo channel"):
            PlivoCallEngine().initiate_call("+1", "+2", "a", "https://call.example")
