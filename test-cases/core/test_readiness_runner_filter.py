"""Unit tests for the targeted-deep filter in the readiness runner.

Source: core/services/readiness/runner.py

The runner filter is the load-bearing piece of "save with an LLM change only
probes LLM live" — if it regresses, save-time targeted deep collapses into
either (a) probing everything (expensive, defeats the point) or (b) probing
nothing (silent regressions in the badge). These tests pin down its exact
behaviour so a future refactor can't silently break it.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from core.services.readiness.runner import Runner
from core.services.readiness.schemas import Category, Depth, Status


def _ctx():
    """Duck-typed CheckContext just complete enough for the registered
    check classes' ``.applies()`` calls to return False safely — we never
    want a live probe firing inside a unit test.
    """
    ctx = MagicMock()
    ctx.depth = Depth.DEEP
    ctx.agent = SimpleNamespace(id="agent-uuid")
    ctx.config = SimpleNamespace(id="config-uuid")
    ctx.tools = []
    ctx.mcp_servers = []
    ctx.knowledge_bases = []
    ctx.phone_numbers = []
    ctx.is_s2s = False
    # LLM/STT/TTS legs — provider/model unset so `.applies()` short-circuits.
    empty_leg = SimpleNamespace(
        provider=None, model=None, api_key=None, decrypted_key=None,
        provider_id=None, model_id=None, settings={},
    )
    ctx.llm = empty_leg
    ctx.stt = empty_leg
    ctx.tts = empty_leg
    ctx.voice = None
    ctx.db = MagicMock()
    ctx.org_id = "org-uuid"
    return ctx


class TestTargetedDeepFilter:
    """`Runner.run(ctx, deep_categories=...)` must:
      1. Still run ALL shallow checks (they carry the URL-shape / key-decrypt
         signals that don't care what category the save touched).
      2. SKIP deep checks whose category isn't in the filter set — with a
         marker string the frontend uses to preserve prior status via
         `mergeReadinessReports`.
      3. Attempt to run deep checks whose category IS in the set (they may
         still applies-skip for their own reasons — that's fine).
    """

    def test_non_matching_deep_checks_marked_unchanged(self):
        """LLM-only save → STT/TTS/tools/MCP deep checks return SKIPPED with
        the 'unchanged on this save' marker so the frontend merge helper
        can carry over their previous state."""
        ctx = _ctx()
        report = asyncio.run(Runner().run(ctx, deep_categories={Category.LLM}))

        by_id = {c.check_id: c for c in report.checks}
        # These are the deep checks in categories NOT in the filter set.
        non_filtered_deep_ids = [
            "stt.provider_reachable",
            "tts.provider_reachable",
            "tools.reachable",
            "mcp_servers.reachable",
        ]
        for cid in non_filtered_deep_ids:
            entry = by_id.get(cid)
            assert entry is not None, f"deep check {cid} missing from report"
            assert entry.status == Status.SKIPPED, (
                f"{cid} should be SKIPPED by filter, got {entry.status}"
            )
            # This exact substring is depended on by the frontend's
            # `mergeReadinessReports`. Do not change without updating both.
            assert "Not re-probed on this save" in (entry.skip_reason or entry.message)

    def test_matching_deep_check_still_runs(self):
        """LLM in the filter set → LLM deep check is NOT filter-skipped. It
        may still `applies-skip` (empty context has no provider), but the
        skip_reason will be the check's own, not the filter marker."""
        ctx = _ctx()
        report = asyncio.run(Runner().run(ctx, deep_categories={Category.LLM}))
        by_id = {c.check_id: c for c in report.checks}
        entry = by_id["llm.provider_reachable"]
        # Empty ctx → applies() returns False → SKIPPED for its own reason.
        # The important assertion is: it did NOT get the targeted-filter marker.
        assert "Not re-probed on this save" not in (entry.skip_reason or entry.message)

    def test_shallow_checks_always_run(self):
        """Shallow checks are unaffected by the deep filter — they still
        appear in the report with real statuses. Without this, the filter
        would silently drop URL-shape / key-decrypt signals every save."""
        ctx = _ctx()
        report = asyncio.run(Runner().run(ctx, deep_categories={Category.LLM}))
        by_id = {c.check_id: c for c in report.checks}
        # Pick a representative shallow check that always runs.
        entry = by_id["llm.provider_configured"]
        # Its reason should NOT be the filter marker — it should be either
        # a real PASS/FAIL or its own applies-skip.
        assert "Not re-probed on this save" not in (entry.skip_reason or entry.message)

    def test_no_filter_runs_everything(self):
        """`deep_categories=None` (publish gate / manual Test button path)
        must run every deep check just like the pre-targeted-deep world."""
        ctx = _ctx()
        report = asyncio.run(Runner().run(ctx))
        for c in report.checks:
            # Nothing in the report should carry the filter marker when no
            # filter was passed — this is the publish-gate guarantee.
            assert "Not re-probed on this save" not in (c.skip_reason or c.message)
