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

These tests fail loudly if the backend values change, so a backend edit can't
silently diverge from the frontend copy. If one of these tests fails because you
changed a backend value on purpose, update the paired constant in
`frontend/src/services/readinessService.ts` (and the reason the FE keeps a copy)
in the SAME change.
"""

from __future__ import annotations

from core.services.readiness.consolidation import _SUPERSEDED_BY_DEEP
from core.services.readiness.runner import TARGETED_DEEP_SKIP_PREFIX


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
