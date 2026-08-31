"""Unit tests for cross-check consolidation.

Source: core/services/readiness/consolidation.py

Pins the "deep supersedes shallow" rule that stops one resource from showing
twice (the shallow OAuth heads-up + the deep reachable result). Pure function,
so no DB / async needed.
"""

from __future__ import annotations

from core.services.readiness.consolidation import suppress_redundant_shallow_checks
from core.services.readiness.schemas import Category, CheckResult, Severity, Status


def _r(check_id: str, category: Category, status: Status) -> CheckResult:
    return CheckResult(
        check_id=check_id,
        category=category,
        severity=Severity.WARNING,
        status=status,
        message="x",
    )


class TestSuppressRedundantShallowChecks:
    def test_deep_fail_supersedes_shallow_oauth(self):
        """MCP deep probe failed for a server → drop its shallow OAuth heads-up,
        keep the deep row and the configured summary."""
        results = [
            _r("mcp_servers.oauth_token_valid:s1", Category.MCP_SERVERS, Status.FAIL),
            _r("mcp_servers.reachable:s1", Category.MCP_SERVERS, Status.FAIL),
            _r("mcp_servers.configured", Category.MCP_SERVERS, Status.PASS),
        ]
        ids = [r.check_id for r in suppress_redundant_shallow_checks(results)]
        assert "mcp_servers.oauth_token_valid:s1" not in ids
        assert "mcp_servers.reachable:s1" in ids
        assert "mcp_servers.configured" in ids

    def test_deep_pass_supersedes_shallow_oauth(self):
        """Deep probe PASSED (summary row) → the 'token may be expired' heads-up
        is now stale, drop it."""
        results = [
            _r("tools.oauth_token_valid:t1", Category.TOOLS, Status.FAIL),
            _r("tools.reachable", Category.TOOLS, Status.PASS),
        ]
        ids = [r.check_id for r in suppress_redundant_shallow_checks(results)]
        assert "tools.oauth_token_valid:t1" not in ids
        assert "tools.reachable" in ids

    def test_shallow_only_run_keeps_heads_up(self):
        """No reachable result at all (shallow-only badge run) → keep the
        heads-up; it's the only signal available."""
        results = [
            _r("mcp_servers.oauth_token_valid:s1", Category.MCP_SERVERS, Status.FAIL),
            _r("mcp_servers.configured", Category.MCP_SERVERS, Status.PASS),
        ]
        ids = [r.check_id for r in suppress_redundant_shallow_checks(results)]
        assert "mcp_servers.oauth_token_valid:s1" in ids

    def test_skipped_deep_is_not_authoritative(self):
        """Deep probe filtered/skipped (e.g. targeted-deep, rate-limited) → not
        a real answer, so the heads-up stays."""
        results = [
            _r("tools.oauth_token_valid:t1", Category.TOOLS, Status.FAIL),
            _r("tools.reachable", Category.TOOLS, Status.SKIPPED),
        ]
        ids = [r.check_id for r in suppress_redundant_shallow_checks(results)]
        assert "tools.oauth_token_valid:t1" in ids

    def test_categories_are_independent(self):
        """MCP deep ran, Tools deep didn't → only MCP's heads-up is dropped."""
        results = [
            _r("mcp_servers.oauth_token_valid:s1", Category.MCP_SERVERS, Status.FAIL),
            _r("mcp_servers.reachable:s1", Category.MCP_SERVERS, Status.FAIL),
            _r("tools.oauth_token_valid:t1", Category.TOOLS, Status.FAIL),
        ]
        ids = [r.check_id for r in suppress_redundant_shallow_checks(results)]
        assert "mcp_servers.oauth_token_valid:s1" not in ids
        assert "tools.oauth_token_valid:t1" in ids

    def test_no_deep_checks_returns_input_unchanged(self):
        results = [_r("llm.provider_configured", Category.LLM, Status.PASS)]
        assert suppress_redundant_shallow_checks(results) == results
