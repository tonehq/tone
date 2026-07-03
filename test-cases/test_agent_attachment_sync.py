"""Unit tests for the ``agent_ids`` full-sync on tool / MCP upsert.

Exercises ``_sync_agent_attachments`` in both ``ToolService`` and
``McpServerService`` with a faked DB layer — no PostgreSQL needed. The two
DB reads the sync performs are fed preset result sets in call order:
  1. agent lookup (id, name, published_config_id) — skipped when desired is empty
  2. current attachments on published versions (1-tuples of agent_id)
The attach/detach service methods are stubbed to record their arguments, so
the tests assert the exact diff the sync computed plus the stamped
``attachment_warnings`` / ``attachment_summary``.

Run:
    pytest test-cases/test_agent_attachment_sync.py -v -o "addopts="
"""

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from core.services.mcp_server_service import McpServerService
from core.services.tool_service import ToolService


class FakeQuery:
    def __init__(self, results):
        self._results = results

    def filter(self, *args, **kwargs):
        return self

    def join(self, *args, **kwargs):
        return self

    def all(self):
        return self._results


class FakeDB:
    """Returns the preset result sets in the order queries are issued."""

    def __init__(self, result_sets):
        self._sets = list(result_sets)

    def query(self, *args, **kwargs):
        return FakeQuery(self._sets.pop(0))


def _agent_row(name: str, published: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        name=name,
        published_config_id=uuid.uuid4() if published else None,
    )


def _tool_service(result_sets) -> ToolService:
    svc = ToolService.__new__(ToolService)
    svc.db = FakeDB(result_sets)
    svc._org_id = uuid.uuid4()  # backing field of the read-only ``org_id`` property
    return svc


def _mcp_service(result_sets) -> McpServerService:
    svc = McpServerService.__new__(McpServerService)
    svc.db = FakeDB(result_sets)
    svc._org_id = uuid.uuid4()  # backing field of the read-only ``org_id`` property
    return svc


class TestToolSync:
    def test_attach_only(self):
        a1, a2 = _agent_row("a1"), _agent_row("a2")
        svc = _tool_service([[a1, a2], []])  # lookup, then current (empty)
        calls = {}

        def attach(ids, tid):
            calls["attach"] = list(ids)
            return [object()] * len(ids)

        def detach(ids, tid):
            calls["detach"] = list(ids)

        svc.attach_tool_to_agents = attach
        svc.detach_tool_from_agents = detach

        tool = SimpleNamespace(id=uuid.uuid4())
        svc._sync_agent_attachments(tool, [str(a1.id), str(a2.id)])

        assert sorted(calls["attach"]) == sorted([a1.id, a2.id])
        assert "detach" not in calls
        assert tool.attachment_summary == {"attached": 2, "detached": 0}
        assert tool.attachment_warnings == []

    def test_empty_list_detaches_all(self):
        a1_id, a2_id = uuid.uuid4(), uuid.uuid4()
        # desired empty → agent lookup is skipped; only the current query runs.
        svc = _tool_service([[(a1_id,), (a2_id,)]])
        calls = {}
        svc.attach_tool_to_agents = lambda ids, tid: calls.setdefault("attach", list(ids))
        svc.detach_tool_from_agents = lambda ids, tid: calls.setdefault("detach", list(ids))

        tool = SimpleNamespace(id=uuid.uuid4())
        svc._sync_agent_attachments(tool, [])

        assert "attach" not in calls
        assert sorted(calls["detach"]) == sorted([a1_id, a2_id])
        assert tool.attachment_summary == {"attached": 0, "detached": 2}
        assert tool.attachment_warnings == []

    def test_mixed_attach_detach_with_skips(self):
        published = _agent_row("published-agent")
        unpublished = _agent_row("draft-agent", published=False)
        unknown_id = uuid.uuid4()  # not in the org — absent from the lookup
        currently_attached = uuid.uuid4()  # attached but not in desired → detach

        svc = _tool_service([[published, unpublished], [(currently_attached,)]])
        calls = {}

        def attach(ids, tid):
            calls["attach"] = list(ids)
            return [object()] * len(ids)

        svc.attach_tool_to_agents = attach
        svc.detach_tool_from_agents = lambda ids, tid: calls.setdefault("detach", list(ids))

        tool = SimpleNamespace(id=uuid.uuid4())
        svc._sync_agent_attachments(
            tool, [str(published.id), str(unpublished.id), str(unknown_id)]
        )

        assert calls["attach"] == [published.id]
        assert calls["detach"] == [currently_attached]
        assert tool.attachment_summary == {"attached": 1, "detached": 1}
        assert any(str(unknown_id) in w for w in tool.attachment_warnings)
        assert any("draft-agent" in w for w in tool.attachment_warnings)

    def test_attach_failure_becomes_warning_not_error(self):
        a1 = _agent_row("a1")
        svc = _tool_service([[a1], []])

        def attach(ids, tid):
            raise HTTPException(status_code=400, detail="missing scopes")

        svc.attach_tool_to_agents = attach
        svc.detach_tool_from_agents = lambda ids, tid: None

        tool = SimpleNamespace(id=uuid.uuid4())
        svc._sync_agent_attachments(tool, [str(a1.id)])  # must not raise

        assert tool.attachment_summary == {"attached": 0, "detached": 0}
        assert tool.attachment_warnings == ["Attach failed: missing scopes"]

    def test_noop_when_already_in_sync(self):
        a1 = _agent_row("a1")
        svc = _tool_service([[a1], [(a1.id,)]])
        svc.attach_tool_to_agents = lambda ids, tid: pytest.fail("attach must not run")
        svc.detach_tool_from_agents = lambda ids, tid: pytest.fail("detach must not run")

        tool = SimpleNamespace(id=uuid.uuid4())
        svc._sync_agent_attachments(tool, [str(a1.id)])

        assert tool.attachment_summary == {"attached": 0, "detached": 0}
        assert tool.attachment_warnings == []

    def test_malformed_ids_raise_400(self):
        svc = _tool_service([])
        tool = SimpleNamespace(id=uuid.uuid4())
        with pytest.raises(HTTPException) as exc:
            svc._sync_agent_attachments(tool, ["not-a-uuid"])
        assert exc.value.status_code == 400


class TestMcpSync:
    def test_attach_and_detach_counts(self):
        new_agent = _agent_row("new-agent")
        stale_id = uuid.uuid4()
        svc = _mcp_service([[new_agent], [(stale_id,)]])
        calls = {}
        svc.attach_to_agents = lambda mid, ids: calls.setdefault("attach", (mid, list(ids)))
        svc.detach_from_agents = lambda mid, ids: calls.setdefault("detach", (mid, list(ids)))

        server = SimpleNamespace(id=uuid.uuid4())
        svc._sync_agent_attachments(server, [str(new_agent.id)])

        assert calls["attach"] == (server.id, [new_agent.id])
        assert calls["detach"] == (server.id, [stale_id])
        assert server.attachment_summary == {"attached": 1, "detached": 1}
        assert server.attachment_warnings == []

    def test_empty_list_detaches_all(self):
        a1_id = uuid.uuid4()
        svc = _mcp_service([[(a1_id,)]])
        calls = {}
        svc.attach_to_agents = lambda mid, ids: calls.setdefault("attach", list(ids))
        svc.detach_from_agents = lambda mid, ids: calls.setdefault("detach", list(ids))

        server = SimpleNamespace(id=uuid.uuid4())
        svc._sync_agent_attachments(server, [])

        assert "attach" not in calls
        assert calls["detach"] == [a1_id]
        assert server.attachment_summary == {"attached": 0, "detached": 1}
