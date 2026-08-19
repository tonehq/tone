"""Turn OFF every DeepEval outbound telemetry / auto-update / error-reporting
beacon BEFORE ``deepeval`` is imported anywhere in the process.

DeepEval fires PostHog + Sentry beacons on import unless these env vars are
already set (see the ``telemetry`` module inside the deepeval package). We
also opt out of its "update available" nag so worker logs stay clean.

Import order matters: this module is imported at the top of
``core.services.evals.deepeval.__init__`` so the env vars are stamped
BEFORE the first ``import deepeval`` anywhere in the worker process. Don't
import this module from a spot that runs AFTER the first deepeval import —
the opt-outs won't take effect retroactively.
"""

from __future__ import annotations

import os

_OPT_OUT_ENV: dict[str, str] = {
    # PostHog usage beacons (DeepEval OSS).
    "DEEPEVAL_TELEMETRY_OPT_OUT": "1",
    # Sentry crash reports.
    "ERROR_REPORTING": "NO",
    # "New version available" nag printed to stderr on import.
    "DEEPEVAL_UPDATE_WARNING_OPT_IN": "NO",
}


def opt_out() -> None:
    """Stamp the opt-out env vars if the operator hasn't already set them.
    Never overrides an explicit value so debugging with telemetry ON is
    still possible via ``DEEPEVAL_TELEMETRY_OPT_OUT=0``."""
    for key, value in _OPT_OUT_ENV.items():
        os.environ.setdefault(key, value)


# Fire on import — the package __init__ imports this module first so the
# vars are set before deepeval loads.
opt_out()
