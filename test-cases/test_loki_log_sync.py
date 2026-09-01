"""Hermetic unit tests for the per-call Loki -> Postgres log sync.

No live database, no network: the Loki HTTP layer is stubbed (fake httpx.Client)
and the DB upsert is simulated by capturing the wholesale ``logs`` array written
per call (mimicking the real ``on_conflict(call_id) do update`` replace). Covers
the parser, fingerprint, LokiClient retry/backoff, the sync service (array build
+ idempotent re-run + short-circuits + pagination + clock skew), and the
post-call action enqueue guard.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

from core.services import loki_client as loki_client_module
from core.services.loki_client import LokiClient, LokiError, LokiLine
from core.services.log_parser import extract_trace_id, fingerprint, parse_line
from core.services.pipeline_log_sync_service import PipelineLogSyncService
from shared.config import settings


# ── log_parser ──────────────────────────────────────────────────────────────

def test_parse_line_matches_loguru_format():
    line = (
        "2026-07-17 11:09:21.123 | INFO     | core.bot:run_bot:42 | "
        "trace_id=abc12345-agent-call | hello world"
    )
    parsed = parse_line(line)
    assert parsed["level"] == "INFO"
    assert parsed["logger_name"] == "core.bot"
    assert parsed["message"] == "hello world"


def test_parse_line_non_matching_keeps_whole_line():
    line = "Traceback (most recent call last):"
    parsed = parse_line(line)
    assert parsed["level"] is None
    assert parsed["logger_name"] is None
    assert parsed["message"] == line  # never dropped


def test_extract_trace_id():
    line = (
        "2026-07-17 11:09:21.123 | INFO     | core.bot:run_bot:42 | "
        "trace_id=abc12345-agent-call | hi"
    )
    assert extract_trace_id(line) == "abc12345-agent-call"
    # A non-loguru / continuation line carries no token.
    assert extract_trace_id("Traceback (most recent call last):") is None


def test_parse_line_strips_job_id_field():
    """Background-job lines carry a ``job_id=...`` field between ``trace_id`` and
    the message (core/logging._LOG_FORMAT). The parser must consume it so the
    stored message is clean — never prefixed with ``job_id=99 | ``."""
    line = (
        "2026-07-17 11:09:21.123 | INFO     | core.services.ingestion_queue:ingest_upload:90 | "
        "trace_id=abc12345-ing-run7 | job_id=99 | [ingestion] worker picked job"
    )
    parsed = parse_line(line)
    assert parsed["level"] == "INFO"
    assert parsed["logger_name"] == "core.services.ingestion_queue"
    assert parsed["message"] == "[ingestion] worker picked job"


def test_parse_line_job_id_none_and_message_with_pipes():
    line = (
        "2026-07-17 11:09:21.123 | INFO     | core.x:f:9 | "
        "trace_id=abc-1-2 | job_id=none | a | b | c"
    )
    parsed = parse_line(line)
    assert parsed["message"] == "a | b | c"  # pipes in message preserved


def test_extract_trace_id_with_job_id_field_present():
    line = (
        "2026-07-17 11:09:21.123 | INFO     | core.x:f:9 | "
        "trace_id=abc12345-agent-call | job_id=42 | hi"
    )
    assert extract_trace_id(line) == "abc12345-agent-call"


def test_fingerprint_is_label_order_independent():
    line = "some log line"
    a = fingerprint(123, {"app": "tone", "pod": "x"}, line)
    b = fingerprint(123, {"pod": "x", "app": "tone"}, line)
    assert a == b


def test_fingerprint_changes_with_content():
    assert fingerprint(1, {"a": "1"}, "line") != fingerprint(2, {"a": "1"}, "line")
    assert fingerprint(1, {"a": "1"}, "line") != fingerprint(1, {"a": "1"}, "other")


# ── LokiClient retry/backoff (fake httpx, no network, no real sleeps) ─────────

class _FakeResp:
    def __init__(self, status_code, *, json_body=None, headers=None, text=""):
        self.status_code = status_code
        self._json = json_body or {}
        self.headers = headers or {}
        self.text = text

    def json(self):
        return self._json


class _FakeClient:
    """Pops one behavior per .get(); a behavior is a _FakeResp or an Exception."""

    behaviors: list = []

    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get(self, *a, **k):
        behavior = type(self).behaviors.pop(0)
        if isinstance(behavior, Exception):
            raise behavior
        return behavior


@pytest.fixture
def fake_httpx(monkeypatch):
    monkeypatch.setattr(loki_client_module.time, "sleep", lambda *_: None)  # no real backoff
    monkeypatch.setattr(loki_client_module.httpx, "Client", _FakeClient)
    yield _FakeClient
    _FakeClient.behaviors = []


def _ok_body():
    return {"data": {"result": [{"stream": {"app": "tone"}, "values": [["100", "line-a"], ["200", "line-b"]]}]}}


def test_query_range_happy_path(fake_httpx):
    fake_httpx.behaviors = [_FakeResp(200, json_body=_ok_body())]
    lines = LokiClient(query_url="http://loki/query_range", user="u", token="t").query_range(
        "q", 0, 1000, limit=10
    )
    assert [(l.ts_ns, l.line) for l in lines] == [(100, "line-a"), (200, "line-b")]
    assert lines[0].labels == {"app": "tone"}


def test_query_range_429_retry_after_then_success(fake_httpx):
    fake_httpx.behaviors = [
        _FakeResp(429, headers={"Retry-After": "0"}),
        _FakeResp(200, json_body=_ok_body()),
    ]
    lines = LokiClient(query_url="http://loki", user="u", token="t", max_retries=3).query_range(
        "q", 0, 1000, limit=10
    )
    assert len(lines) == 2


def test_query_range_5xx_exhausts_retries(fake_httpx):
    fake_httpx.behaviors = [_FakeResp(500), _FakeResp(500), _FakeResp(500)]
    with pytest.raises(LokiError) as exc:
        LokiClient(query_url="http://loki", user="u", token="t", max_retries=2).query_range(
            "q", 0, 1000, limit=10
        )
    assert exc.value.status_code == 500


def test_query_range_timeout_retried_then_success(fake_httpx):
    fake_httpx.behaviors = [
        httpx.TimeoutException("timeout"),
        _FakeResp(200, json_body=_ok_body()),
    ]
    lines = LokiClient(query_url="http://loki", user="u", token="t", max_retries=3).query_range(
        "q", 0, 1000, limit=10
    )
    assert len(lines) == 2


def test_query_range_401_is_non_retryable(fake_httpx):
    fake_httpx.behaviors = [_FakeResp(401)]
    with pytest.raises(LokiError) as exc:
        LokiClient(query_url="http://loki", user="u", token="t").query_range("q", 0, 1000, limit=10)
    assert exc.value.status_code == 401


# ── PipelineLogSyncService ───────────────────────────────────────────────────

class _FakeDB:
    """Captures the wholesale ``logs`` array written per call (upsert-replace)."""

    def __init__(self):
        self.stored: dict = {}    # call_id -> list[entry] (the row's logs array)
        self.upserts: list = []   # (call, entries) per _upsert_call


def _stub_service(monkeypatch, db, pages):
    """Return a service whose LokiClient yields ``pages`` (list of line-lists) and
    whose _upsert_call replaces the call's stored array against ``db``."""
    monkeypatch.setattr(settings, "loki_read_configured", lambda: True)
    monkeypatch.setattr(settings, "LOKI_SYNC_PAGE_LIMIT", 2)

    class _StubClient:
        def __init__(self, *a, **k):
            self._pages = list(pages)

        def query_range(self, *a, **k):
            return self._pages.pop(0) if self._pages else []

    monkeypatch.setattr(
        "core.services.pipeline_log_sync_service.LokiClient", _StubClient
    )

    def fake_upsert(self, call, entries):
        # Wholesale replace — exactly what on_conflict(call_id) do update does.
        db.stored[call.id] = list(entries)
        db.upserts.append((call, list(entries)))
        return len(entries)

    monkeypatch.setattr(PipelineLogSyncService, "_upsert_call", fake_upsert)
    return PipelineLogSyncService(SimpleNamespace(), org_id=uuid.uuid4())


def _make_call(**over):
    now = datetime.now(timezone.utc)
    base = dict(
        id=uuid.uuid4(),
        trace_id="abc12345-agent-call",
        organization_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        started_at=now - timedelta(minutes=2),
        ended_at=now - timedelta(minutes=1),
        created_at=now - timedelta(minutes=3),
    )
    base.update(over)
    return SimpleNamespace(**base)


def _line(ts_ns, text):
    return LokiLine(ts_ns=ts_ns, line=text, labels={"app": "tone"})


def _window_ns(offset: int = 0) -> int:
    """A nanosecond timestamp inside a fresh call's window (real Loki lines fall
    between start_ns and end_ns, which are ~1.7e18 — toy values trip the
    'cursor can't advance' pagination guard)."""
    return int((datetime.now(timezone.utc) - timedelta(seconds=60)).timestamp() * 1_000_000_000) + offset


def test_sync_builds_array_and_stamps_from_call(monkeypatch):
    db = _FakeDB()
    call = _make_call()
    svc = _stub_service(
        monkeypatch, db,
        pages=[[_line(_window_ns(1), "a"), _line(_window_ns(2), "b")], [_line(_window_ns(3), "c")]],
    )

    result = svc.sync_call(call)

    assert result.stored == 3
    assert result.pages == 2  # full first page forces a second fetch

    entries = db.stored[call.id]
    # One row per call: all lines land in a single time-ordered array.
    assert [e["raw_line"] for e in entries] == ["a", "b", "c"]
    assert [e["ts_ns"] for e in entries] == sorted(e["ts_ns"] for e in entries)
    # Entry shape — identity is NOT repeated per line; it lives on the row.
    for e in entries:
        assert set(e) == {"ts", "ts_ns", "level", "logger_name", "message", "raw_line"}
    # Identity stamped from the Call onto the row (via _upsert_call).
    upsert_call, _ = db.upserts[-1]
    assert upsert_call.id == call.id
    assert upsert_call.organization_id == call.organization_id
    assert upsert_call.agent_id == call.agent_id
    assert upsert_call.trace_id == call.trace_id


def test_sync_is_idempotent_on_rerun(monkeypatch):
    db = _FakeDB()
    call = _make_call()
    pages = [[_line(_window_ns(1), "a"), _line(_window_ns(2), "b")], [_line(_window_ns(3), "c")]]
    svc1 = _stub_service(monkeypatch, db, pages=[list(p) for p in pages])
    assert svc1.sync_call(call).stored == 3

    # Second run re-reads the same window and replaces the array wholesale:
    # the stored row still has exactly the same 3 lines, never 6.
    svc2 = _stub_service(monkeypatch, db, pages=[list(p) for p in pages])
    second = svc2.sync_call(call)
    assert second.stored == 3
    assert [e["raw_line"] for e in db.stored[call.id]] == ["a", "b", "c"]


def test_sync_short_circuits_when_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "loki_read_configured", lambda: False)
    svc = PipelineLogSyncService(SimpleNamespace(), org_id=uuid.uuid4())
    result = svc.sync_call(_make_call())
    assert result.configured is False
    assert result.stored == 0


def test_sync_short_circuits_without_trace_id(monkeypatch):
    monkeypatch.setattr(settings, "loki_read_configured", lambda: True)
    svc = PipelineLogSyncService(SimpleNamespace(), org_id=uuid.uuid4())
    result = svc.sync_call(_make_call(trace_id=None))
    assert result.stored == 0
    assert "trace_id" in result.message


def test_sync_drops_foreign_prefix_collision(monkeypatch):
    """A different call sharing our 8-char short-uuid prefix must not have its
    lines misattributed to this call."""
    db = _FakeDB()
    call = _make_call(trace_id="abc12345-agentX-callX")
    ours = (
        "2026-07-17 11:09:21.123 | INFO     | core.bot:run:1 | "
        "trace_id=abc12345-agentX-callX | ours"
    )
    foreign = (
        "2026-07-17 11:09:21.124 | INFO     | core.bot:run:1 | "
        "trace_id=abc12345-agentY-callY | theirs"
    )
    svc = _stub_service(
        monkeypatch, db,
        pages=[[_line(_window_ns(1), ours), _line(_window_ns(2), foreign)]],
    )

    result = svc.sync_call(call)

    assert result.stored == 1
    assert [e["raw_line"] for e in db.stored[call.id]] == [ours]


def test_sync_keeps_early_prefix_only_lines(monkeypatch):
    """Lines logged before the agent/call id are known carry only the short-uuid
    prefix as their trace token — they must still be stored for this call."""
    db = _FakeDB()
    call = _make_call(trace_id="abc12345-agentX-callX")
    early = (
        "2026-07-17 11:09:21.123 | INFO     | core.bot:bot:1 | "
        "trace_id=abc12345 | booting"
    )
    svc = _stub_service(monkeypatch, db, pages=[[_line(_window_ns(1), early)]])

    result = svc.sync_call(call)

    assert result.stored == 1
    assert db.stored[call.id][0]["raw_line"] == early


def test_sync_clamps_future_ended_at(monkeypatch):
    """Clock skew: ended_at in the future must not push the window end past now+buffer."""
    db = _FakeDB()
    future = datetime.now(timezone.utc) + timedelta(days=1)
    call = _make_call(ended_at=future)
    svc = _stub_service(monkeypatch, db, pages=[[_line(100, "a")]])
    result = svc.sync_call(call)
    now = datetime.now(timezone.utc)
    # end clamped to ~now + POST_BUFFER, nowhere near a day out.
    assert result.window_end <= now + timedelta(seconds=settings.LOKI_SYNC_POST_BUFFER_SECONDS + 5)


def test_sync_call_by_id_returns_none_for_missing_call(monkeypatch):
    monkeypatch.setattr(settings, "loki_read_configured", lambda: True)

    class _Q:
        def filter(self, *a, **k):
            return self

        def first(self):
            return None

    svc = PipelineLogSyncService(SimpleNamespace(), org_id=uuid.uuid4())
    monkeypatch.setattr(svc, "query", lambda model: _Q())
    assert svc.sync_call_by_id(uuid.uuid4()) is None  # -> endpoint 404


# ── SyncLokiLogsAction enqueue guard ─────────────────────────────────────────

def test_action_enqueues_when_configured(monkeypatch):
    from core.services.post_call.actions import sync_loki_logs as action_mod

    calls = []
    monkeypatch.setattr(settings, "loki_read_configured", lambda: True)
    monkeypatch.setattr(action_mod, "enqueue_loki_log_sync_sync", lambda cid, **k: calls.append((cid, k)))

    call = _make_call()
    action_mod.SyncLokiLogsAction().enqueue(call)
    assert calls and calls[0][0] == call.id
    assert calls[0][1]["delay_seconds"] == settings.LOKI_SYNC_DELAY_SECONDS


def test_action_noop_without_trace_id(monkeypatch):
    from core.services.post_call.actions import sync_loki_logs as action_mod

    calls = []
    monkeypatch.setattr(settings, "loki_read_configured", lambda: True)
    monkeypatch.setattr(action_mod, "enqueue_loki_log_sync_sync", lambda cid, **k: calls.append(cid))

    action_mod.SyncLokiLogsAction().enqueue(_make_call(trace_id=None))
    assert calls == []


def test_action_noop_when_not_configured(monkeypatch):
    from core.services.post_call.actions import sync_loki_logs as action_mod

    calls = []
    monkeypatch.setattr(settings, "loki_read_configured", lambda: False)
    monkeypatch.setattr(action_mod, "enqueue_loki_log_sync_sync", lambda cid, **k: calls.append(cid))

    action_mod.SyncLokiLogsAction().enqueue(_make_call())
    assert calls == []
