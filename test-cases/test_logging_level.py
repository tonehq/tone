"""Unit tests for log-level resolution.

Covers the process baseline (core/logging.py) and the DB hierarchy resolver
(core/services/log_level_resolver.py): agent > organization > env baseline > INFO,
the transient-agent DB-safety guard, and setup_logging() level handling. No DB
connection — the org lookup is exercised with a fake session.
"""

import uuid

import pytest

import core.logging as L
from core.services.log_level_resolver import resolve_call_log_level


@pytest.fixture(autouse=True)
def _restore_sink():
    """setup_logging() reconfigures the global sink; restore a sane default after
    each test so ordering can't leak a level."""
    yield
    L.setup_logging("INFO")


# --- fakes -----------------------------------------------------------------

class _Agent:
    """Plain (non-ORM) stand-in — inspect() fails on it, so it's treated as
    NOT transient (a real DB-backed agent)."""

    def __init__(self, log_level=None, organization_id=None):
        self.log_level = log_level
        self.organization_id = organization_id


class _Org:
    def __init__(self, log_level=None):
        self.log_level = log_level


class _FakeQuery:
    def __init__(self, scalar_value):
        self._v = scalar_value

    def filter(self, *a, **k):
        return self

    def scalar(self):
        return self._v


class _FakeDB:
    """Returns a fixed organizations.log_level for any query. Records whether it
    was queried so tests can assert the transient guard skipped it."""

    def __init__(self, org_level):
        self._org_level = org_level
        self.queried = False

    def query(self, *a, **k):
        self.queried = True
        return _FakeQuery(self._org_level)


# --- normalize -------------------------------------------------------------

class TestNormalizeLevel:
    @pytest.mark.parametrize("value,expected", [(" debug ", "DEBUG"), ("info", "INFO"), ("TRACE", "TRACE")])
    def test_valid(self, value, expected):
        assert L._normalize_level(value) == expected

    @pytest.mark.parametrize("bad", ["", "   ", None, "LOUD", "verbose", 0])
    def test_blank_or_invalid(self, bad):
        assert L._normalize_level(bad) is None


# --- process baseline ------------------------------------------------------

class TestResolveLevel:
    def test_env_used(self, monkeypatch):
        from shared.config import settings
        monkeypatch.setattr(settings, "LOG_LEVEL", "DEBUG")
        assert L.resolve_level() == ("DEBUG", "env")

    def test_default_when_env_blank(self, monkeypatch):
        from shared.config import settings
        monkeypatch.setattr(settings, "LOG_LEVEL", "")
        assert L.resolve_level() == ("INFO", "default")

    def test_default_when_env_invalid(self, monkeypatch):
        from shared.config import settings
        monkeypatch.setattr(settings, "LOG_LEVEL", "NONSENSE")
        assert L.resolve_level() == ("INFO", "default")


# --- DB hierarchy resolver -------------------------------------------------

class TestResolveCallLogLevel:
    def test_agent_level_wins(self):
        db = _FakeDB("WARNING")
        level, source = resolve_call_log_level(db, agent=_Agent(log_level="debug", organization_id=uuid.uuid4()))
        assert (level, source) == ("DEBUG", "agent")
        assert db.queried is False  # agent level short-circuits before any org query

    def test_falls_through_to_org(self):
        db = _FakeDB("trace")
        level, source = resolve_call_log_level(db, agent=_Agent(log_level=None, organization_id=uuid.uuid4()))
        assert (level, source) == ("TRACE", "organization")
        assert db.queried is True

    def test_org_object_wins_without_query(self):
        db = _FakeDB("DEBUG")
        level, source = resolve_call_log_level(db, org=_Org(log_level="warning"))
        assert (level, source) == ("WARNING", "organization")
        assert db.queried is False

    def test_env_fallback_when_nothing_set(self, monkeypatch):
        from shared.config import settings
        monkeypatch.setattr(settings, "LOG_LEVEL", "INFO")
        db = _FakeDB(None)  # org row has NULL log_level
        level, source = resolve_call_log_level(db, agent=_Agent(log_level=None, organization_id=uuid.uuid4()))
        assert (level, source) == ("INFO", "env")

    def test_no_db_no_query(self):
        # Without a db session there is nothing to query — env baseline applies.
        level, source = resolve_call_log_level(None, agent=_Agent(log_level=None, organization_id=uuid.uuid4()))
        assert source in ("env", "default")

    def test_transient_agent_skips_db_query(self, monkeypatch):
        """A reconstructed (transient) agent must NOT trigger an org query — that
        would force an expensive DB connection in a prefetch subprocess."""
        from sqlalchemy.orm import make_transient

        from core.models.agent import Agent

        monkeypatch.setattr("shared.config.settings.LOG_LEVEL", "INFO")
        a = Agent(organization_id=uuid.uuid4())
        make_transient(a)
        a.log_level = None
        db = _FakeDB("DEBUG")
        level, source = resolve_call_log_level(db, agent=a)
        assert db.queried is False  # guard held
        assert source in ("env", "default")

    def test_transient_agent_with_own_level(self):
        """A transient agent that *does* carry log_level (serialized) still resolves
        it — no query needed."""
        from sqlalchemy.orm import make_transient

        from core.models.agent import Agent

        a = Agent(organization_id=uuid.uuid4())
        make_transient(a)
        a.log_level = "TRACE"
        db = _FakeDB("DEBUG")
        assert resolve_call_log_level(db, agent=a) == ("TRACE", "agent")
        assert db.queried is False


# --- setup_logging ---------------------------------------------------------

class TestSetupLogging:
    def test_explicit_level_wins(self):
        assert L.setup_logging("DEBUG") == "DEBUG"
        assert L.get_applied_level() == "DEBUG"

    def test_invalid_explicit_falls_back_to_baseline(self, monkeypatch):
        from shared.config import settings
        monkeypatch.setattr(settings, "LOG_LEVEL", "INFO")
        assert L.setup_logging("garbage") == "INFO"
