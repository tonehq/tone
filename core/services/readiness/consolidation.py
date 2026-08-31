"""Cross-check consolidation for a readiness result set.

Some categories carry BOTH a cheap shallow "heads-up" check and an
authoritative deep probe that answer the same question at two confidence
levels. The clearest example is OAuth tokens:

* ``*.oauth_token_valid`` (shallow) — a DB-only heads-up: "this token looks
  expired; runtime will try to refresh — run a deep test to confirm."
* ``*.reachable`` (deep) — actually connects (refreshing the token if needed)
  and reports the *confirmed* outcome.

When the deep probe has run, its result is the truth for that resource, so the
shallow heads-up is redundant — showing both makes one resource appear twice in
the drawer (the exact "same thing shows twice" problem). This module removes
that redundancy in ONE place so:

* the runner stays a pure orchestrator (it just calls this),
* summary counts are computed AFTER de-duplication (correct badge numbers),
* the rule lives in a single, testable function.

The shallow heads-up is only dropped when the deep check actually produced a
real (non-skipped) result — i.e. the deep test genuinely ran. In a shallow-only
run (agent-list badge) no ``*.reachable`` result exists, so the heads-up is
kept: there, it's the only signal available.
"""

from __future__ import annotations

from typing import List, Set, Tuple

from core.services.readiness.schemas import CheckResult, Status


# (shallow heads-up check-id, authoritative deep check-id). When the deep check
# produced a real result, results belonging to the heads-up check are dropped.
# check-ids are matched by prefix so per-resource ids (``<id>:<uuid>``) match too.
_SUPERSEDED_BY_DEEP: Tuple[Tuple[str, str], ...] = (
    ("mcp_servers.oauth_token_valid", "mcp_servers.reachable"),
    ("tools.oauth_token_valid", "tools.reachable"),
)


def _matches(check_id: str, prefix: str) -> bool:
    """True when ``check_id`` is ``prefix`` or a per-resource ``prefix:<id>``."""
    return check_id == prefix or check_id.startswith(f"{prefix}:")


def suppress_redundant_shallow_checks(results: List[CheckResult]) -> List[CheckResult]:
    """Drop shallow heads-up results the deep probe has already superseded.

    Pure function — takes the raw result list and returns a new list with the
    redundant entries removed. Order is preserved. When no deep check ran, the
    input is returned unchanged.
    """
    ran_deep: Set[str] = set()
    for result in results:
        if result.status == Status.SKIPPED:
            continue
        for _headsup, deep in _SUPERSEDED_BY_DEEP:
            if _matches(result.check_id, deep):
                ran_deep.add(deep)

    if not ran_deep:
        return results

    superseded_prefixes = {
        headsup for headsup, deep in _SUPERSEDED_BY_DEEP if deep in ran_deep
    }
    return [
        result
        for result in results
        if not any(_matches(result.check_id, prefix) for prefix in superseded_prefixes)
    ]
