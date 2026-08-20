"""Organization ``settings`` JSONB helpers — the single source of truth for reading typed
values out of the org settings bag so a key name/default is never duplicated across callers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from shared.config import settings as env_settings

# Key in ``Organization.settings`` holding the org's default scheduling timezone (IANA name,
# e.g. "America/New_York"). Kept in sync with the frontend org settings form.
SCHEDULING_TIMEZONE_KEY = "scheduling_timezone"
DEFAULT_SCHEDULING_TIMEZONE = "UTC"


def get_scheduling_timezone(settings: Optional[Mapping[str, Any]]) -> str:
    """Return the org's default scheduling timezone (IANA), falling back to ``UTC``.

    ``settings`` is the org's ``settings`` JSONB (or ``None``). This is the ONE resolver —
    every caller that needs the org's default scheduling timezone goes through it.
    """
    value = (settings or {}).get(SCHEDULING_TIMEZONE_KEY)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return DEFAULT_SCHEDULING_TIMEZONE


# ── Eval settings ─────────────────────────────────────────────────────────
# Per-org overrides for RAG-eval knobs. Every field is optional in the raw
# JSONB — the resolver below falls back through env → hardcoded default so
# an org with no ``eval_settings`` row behaves identically to today.

EVAL_SETTINGS_KEYS: tuple[str, ...] = (
    "auto_run_enabled",
    "generation_model",
    "answer_model",
    "judge_model",
    "judge_engine",
    "top_k",
    "max_context_chars",
    "metric_threshold",
    "metrics_enabled",
    "metric_thresholds",
)

# Hardcoded defaults — the LAST fallback (DB → env → this). Match the
# historical shipping values so behavior is stable when neither DB nor env
# has a value set.
# _DEFAULT_AUTO_RUN_ENABLED is a documentation anchor only — see the
# comment in ``get_eval_settings`` explaining why the current ``_bool_env``
# shape means an unset env resolves to False directly (no separate fallback
# branch). Kept as a named constant so a future ``_bool_env`` returning
# ``Optional[bool]`` can restore the DB → env → hardcoded default chain
# without hunting for the value.
_DEFAULT_AUTO_RUN_ENABLED = False
_DEFAULT_GENERATION_MODEL = "gpt-4o"
_DEFAULT_ANSWER_MODEL = "gpt-4o"
_DEFAULT_JUDGE_MODEL = "gpt-4o"
_DEFAULT_JUDGE_ENGINE = "deepeval"
_DEFAULT_TOP_K = 8
_DEFAULT_MAX_CONTEXT_CHARS = 60000
_DEFAULT_METRIC_THRESHOLD = 0.7
_DEFAULT_METRICS_ENABLED: tuple[str, ...] = (
    "faithfulness",
    "answer_relevancy",
    "contextual_precision",
    "contextual_recall",
    "contextual_relevancy",
    "hallucination",
    "correctness",
)


@dataclass(frozen=True)
class EvalSettings:
    """Resolved per-org RAG-eval configuration. Immutable so callers can't
    mutate it accidentally when passing it down through the eval pipeline.

    Every field has a value at construction time — the resolver
    (:func:`get_eval_settings`) walks the DB → env → hardcoded default chain
    for each key so downstream code never needs to guard for missing values.
    """

    auto_run_enabled: bool
    generation_model: str
    answer_model: str
    judge_model: str
    judge_engine: str
    top_k: int
    max_context_chars: int
    metric_threshold: float
    metrics_enabled: list[str] = field(default_factory=list)
    metric_thresholds: dict[str, float] = field(default_factory=dict)


def _first_non_empty_str(*values: Any) -> Optional[str]:
    for v in values:
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _first_positive_int(*values: Any) -> Optional[int]:
    for v in values:
        if isinstance(v, bool):  # bool is a subclass of int — skip
            continue
        if isinstance(v, int) and v > 0:
            return v
    return None


def _first_valid_ratio(*values: Any) -> Optional[float]:
    for v in values:
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)) and 0.0 < float(v) <= 1.0:
            return float(v)
    return None


def _first_non_empty_list(*values: Any) -> Optional[list[str]]:
    for v in values:
        if isinstance(v, (list, tuple)) and v:
            clean = [str(x).strip() for x in v if isinstance(x, str) and str(x).strip()]
            if clean:
                return clean
    return None


def get_eval_settings(org_eval_settings: Optional[Mapping[str, Any]]) -> EvalSettings:
    """Resolve the org's eval configuration with DB → env → hardcoded fallback.

    ``org_eval_settings`` is the raw ``organizations.eval_settings`` JSONB
    (or ``None`` for orgs that have never opened the Settings → Evaluations
    page). Every returned field is guaranteed to be a valid, typed value —
    no downstream ``or settings.X`` fallbacks needed.

    This is the ONE resolver — every caller that needs an eval knob (RAG
    eval service, judge factory, DeepEval judge service, ingestion complete-
    run auto-trigger) goes through it.
    """
    src: Mapping[str, Any] = org_eval_settings or {}

    # bool — DB overrides env when the key is explicitly present. ``_bool_env``
    # is always defined (returns ``False`` on an unset env var), so there is
    # no separate hardcoded-default branch for this key: an unset env is
    # semantically identical to ``EVAL_AUTO_RUN_ENABLED=false``. Any deployment
    # that wants auto-run ON must set the env or the org-level toggle. The
    # constant ``_DEFAULT_AUTO_RUN_ENABLED`` stays as a documentation anchor
    # so a future change to ``_bool_env`` (returning Optional[bool]) can
    # re-introduce the fallback branch without breaking this contract.
    if "auto_run_enabled" in src and isinstance(src["auto_run_enabled"], bool):
        auto_run_enabled = src["auto_run_enabled"]
    else:
        auto_run_enabled = bool(env_settings.EVAL_AUTO_RUN_ENABLED)

    generation_model = (
        _first_non_empty_str(src.get("generation_model"), env_settings.EVAL_GENERATION_MODEL)
        or _DEFAULT_GENERATION_MODEL
    )
    answer_model = (
        _first_non_empty_str(src.get("answer_model"), env_settings.EVAL_ANSWER_MODEL)
        or _DEFAULT_ANSWER_MODEL
    )
    judge_model = (
        _first_non_empty_str(src.get("judge_model"), env_settings.EVAL_JUDGE_MODEL)
        or _DEFAULT_JUDGE_MODEL
    )
    judge_engine = (
        _first_non_empty_str(src.get("judge_engine"), env_settings.EVAL_JUDGE_ENGINE)
        or _DEFAULT_JUDGE_ENGINE
    )
    top_k = (
        _first_positive_int(src.get("top_k"), env_settings.EVAL_TOP_K)
        or _DEFAULT_TOP_K
    )
    max_context_chars = (
        _first_positive_int(src.get("max_context_chars"), env_settings.EVAL_MAX_CONTEXT_CHARS)
        or _DEFAULT_MAX_CONTEXT_CHARS
    )
    metric_threshold = (
        _first_valid_ratio(src.get("metric_threshold"), env_settings.EVAL_METRIC_THRESHOLD)
        or _DEFAULT_METRIC_THRESHOLD
    )
    metrics_enabled = (
        _first_non_empty_list(src.get("metrics_enabled"), env_settings.EVAL_METRICS_ENABLED)
        or list(_DEFAULT_METRICS_ENABLED)
    )

    # metric_thresholds is a dict of overrides; values validated in the same
    # (0.0, 1.0] range. Missing / invalid → empty dict (no overrides applied).
    raw_overrides = src.get("metric_thresholds")
    metric_thresholds: dict[str, float] = {}
    if isinstance(raw_overrides, Mapping):
        for name, value in raw_overrides.items():
            if not isinstance(name, str) or not name.strip():
                continue
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)) and 0.0 < float(value) <= 1.0:
                metric_thresholds[name.strip()] = float(value)

    return EvalSettings(
        auto_run_enabled=auto_run_enabled,
        generation_model=generation_model,
        answer_model=answer_model,
        judge_model=judge_model,
        judge_engine=judge_engine,
        top_k=top_k,
        max_context_chars=max_context_chars,
        metric_threshold=metric_threshold,
        metrics_enabled=metrics_enabled,
        metric_thresholds=metric_thresholds,
    )


def load_eval_settings_for_org(db, org_id: Any) -> EvalSettings:
    """Convenience: fetch ``organizations.eval_settings`` for ``org_id`` and
    resolve it via :func:`get_eval_settings`. Returns the fully-resolved
    settings even if the org is missing or has no override row set (falls
    through to env → defaults).

    ``db`` is an active SQLAlchemy session. Kept transport-agnostic so
    services, workers, and CLIs all use the same one-liner.
    """
    from core.models.organization import Organization

    if org_id is None:
        return get_eval_settings(None)
    row = (
        db.query(Organization.eval_settings)
        .filter(Organization.id == org_id)
        .first()
    )
    return get_eval_settings(row[0] if row is not None else None)
