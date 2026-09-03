"""Cross-language contract lock between the readiness backend and the frontend.

The frontend (`frontend/src/services/readinessService.ts`) intentionally mirrors
two backend values because the targeted-deep *merge* — stitching a partial save's
result on top of the prior report — happens client-side (the backend
deliberately does NOT persist targeted-deep runs, so it has no cumulative prior
to merge against; see `ReadinessService.check`). Those mirrored values are:

1. `TARGETED_DEEP_SKIP_PREFIX`  ↔  FE `TARGETED_DEEP_SKIP_MARKER`
   The skip-reason prefix the runner stamps on a deep check whose category
   wasn't re-probed. The FE substring-matches it to know which categories to
   carry forward.

2. `_SUPERSEDED_BY_DEEP`  ↔  FE `DEEP_SUPERSEDES_SHALLOW`
   The (shallow-heads-up → authoritative-deep) check-id pairs used to drop a
   redundant shallow row once the deep probe has answered. The FE re-applies
   this after a merge.

3. `Runner._aggregate` counts + `overall_status` thresholds  ↔  FE
   `mergeReadinessReports` / `reportToSummary` (readinessService.ts). The FE
   recomputes both client-side after a targeted-deep merge, so if the backend
   ever re-buckets a severity or changes the ready / warnings / not-ready
   thresholds, the FE copy would silently drift. These tests lock the mapping.

These tests fail loudly if the backend values change, so a backend edit can't
silently diverge from the frontend copy. If one of these tests fails because you
changed a backend value on purpose, update the paired constant in
`frontend/src/services/readinessService.ts` (and the reason the FE keeps a copy)
in the SAME change.
"""

from __future__ import annotations

from core.services.readiness.consolidation import _SUPERSEDED_BY_DEEP
from core.services.readiness.runner import TARGETED_DEEP_SKIP_PREFIX
from core.services.readiness.runner import Runner
from core.services.readiness.schemas import (
    Category,
    CheckResult,
    Depth,
    Severity,
    Status,
)


# Verbatim copies of the frontend constants (readinessService.ts). Kept as plain
# literals here — NOT imported from the backend — so the assertion actually
# compares the two independent definitions rather than an identity check.
_FRONTEND_TARGETED_DEEP_SKIP_MARKER = "Not re-probed on this save"
_FRONTEND_DEEP_SUPERSEDES_SHALLOW = (
    ("mcp_servers.oauth_token_valid", "mcp_servers.reachable"),
    ("tools.oauth_token_valid", "tools.reachable"),
)


def test_targeted_deep_skip_prefix_matches_frontend_marker():
    # FE does `message.includes(TARGETED_DEEP_SKIP_MARKER)`, so the marker must
    # remain a substring the backend prefix begins with.
    assert TARGETED_DEEP_SKIP_PREFIX == _FRONTEND_TARGETED_DEEP_SKIP_MARKER


def test_deep_supersedes_shallow_pairs_match_frontend():
    # Order-independent compare — the FE array order is cosmetic; the pair set
    # is the contract.
    assert set(_SUPERSEDED_BY_DEEP) == set(_FRONTEND_DEEP_SUPERSEDES_SHALLOW)


# ── Count + overall_status parity ────────────────────────────────────────────
# Independent literal re-implementation of the frontend's post-merge derivation
# (readinessService.ts `mergeReadinessReports`). NOT imported from the backend,
# so the assertions compare two definitions rather than an identity.


def _frontend_overall_status(blockers: int, warnings: int) -> str:
    # `blockers > 0 ? 'not_ready' : warnings > 0 ? 'ready_with_warnings' : 'ready'`
    if blockers > 0:
        return "not_ready"
    if warnings > 0:
        return "ready_with_warnings"
    return "ready"


# The exact key set the FE writes into `summary` after a merge.
_FRONTEND_SUMMARY_KEYS = {"blockers", "warnings", "info", "passed", "skipped"}


def _result(status: Status, severity: Severity) -> CheckResult:
    return CheckResult(
        check_id="x",
        category=Category.LLM,
        severity=severity,
        status=status,
        message="m",
    )


def _aggregate(results):
    # `agent_id` / `config_id` are irrelevant to the counts + status derivation.
    return Runner()._aggregate(
        results, depth=Depth.SHALLOW, agent_id=None, config_id=None
    )


def test_summary_keys_match_frontend():
    report = _aggregate([_result(Status.PASS, Severity.INFO)])
    assert set(report.summary.keys()) == _FRONTEND_SUMMARY_KEYS


def test_counts_bucket_by_status_and_severity_like_frontend():
    results = [
        _result(Status.FAIL, Severity.BLOCKER),
        _result(Status.FAIL, Severity.WARNING),
        _result(Status.FAIL, Severity.WARNING),
        _result(Status.FAIL, Severity.INFO),
        _result(Status.PASS, Severity.INFO),
        _result(Status.SKIPPED, Severity.INFO),
    ]
    report = _aggregate(results)
    # Same buckets the FE loop fills: fail→severity, pass→passed, skipped→skipped.
    assert report.summary == {
        "blockers": 1,
        "warnings": 2,
        "info": 1,
        "passed": 1,
        "skipped": 1,
    }


def test_overall_status_thresholds_match_frontend():
    cases = [
        ([_result(Status.FAIL, Severity.BLOCKER), _result(Status.FAIL, Severity.WARNING)], (1, 1)),
        ([_result(Status.FAIL, Severity.WARNING)], (0, 1)),
        ([_result(Status.PASS, Severity.INFO)], (0, 0)),
        # An INFO-severity FAIL is neither a blocker nor a warning → still ready.
        ([_result(Status.FAIL, Severity.INFO)], (0, 0)),
    ]
    for results, (blockers, warnings) in cases:
        report = _aggregate(results)
        assert report.overall_status.value == _frontend_overall_status(blockers, warnings)
