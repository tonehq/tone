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
# Per-org overrides for eval knobs. The JSONB is shaped as two sibling
# sub-objects:
#   {
#     "rag_evals":  { ...RAG (Level-1) knobs... },
#     "llm_evals":  { ...agent-LLM (Level-2) knobs... },
#   }
# so each flavor owns an independent copy of every setting (including its
# own ``auto_run_enabled``). Both sub-objects are optional; the resolvers
# below fall through env → hardcoded default per field so an unconfigured
# org runs on defaults with no explicit setup.

# JSONB slot names — kept as constants so the resolver, validator, and
# tests never disagree on the key names.
RAG_EVAL_SLOT = "rag_evals"
LLM_EVAL_SLOT = "llm_evals"

# Pre-restructure slot for agent-LLM eval knobs. Read-only fallback so orgs
# that saved settings before the {rag_evals, llm_evals} restructure keep
# working; new writes always go to LLM_EVAL_SLOT.
_LEGACY_LLM_SLOT = "agent_llm"

# Key names the RAG resolver treats as evidence that root-level values are
# saved in the pre-restructure FLAT shape. If ANY of these keys is present
# at the JSONB root (and the ``rag_evals`` slot is absent), the resolver
# reads from the root as a compat shim.
_LEGACY_RAG_ROOT_KEYS: frozenset[str] = frozenset({
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
})


def _looks_like_legacy_rag_root(root: Mapping[str, Any]) -> bool:
    """True when the JSONB root carries any RAG key at the top level
    (pre-restructure shape). Used to safely fall back to the root when the
    ``rag_evals`` sub-object is absent."""
    return any(k in root for k in _LEGACY_RAG_ROOT_KEYS)

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
    """Resolve the org's RAG-eval configuration with DB → env → hardcoded fallback.

    ``org_eval_settings`` is the raw ``organizations.eval_settings`` JSONB
    (or ``None`` for orgs that have never opened the Settings → Evaluations
    page). The RAG knobs live under the ``rag_evals`` sub-object; this
    resolver reads from there and falls through env → hardcoded default for
    every unset field — so every returned attribute is a valid typed value
    and downstream code never needs its own ``or DEFAULT`` fallbacks.

    This is the ONE resolver — every caller that needs a RAG eval knob (the
    RAG eval service, the judge factory, the DeepEval judge service, and
    the ingestion complete-run auto-trigger) goes through it.
    """
    root: Mapping[str, Any] = org_eval_settings or {}
    slot = root.get(RAG_EVAL_SLOT)
    if isinstance(slot, Mapping):
        src: Mapping[str, Any] = slot
    else:
        # Back-compat: orgs that saved settings under the pre-restructure
        # FLAT root shape (root-level ``judge_model`` / ``top_k`` / …) still
        # resolve correctly here — a fresh save from the FE lifts them into
        # the ``rag_evals`` slot, but until then we read from the root so an
        # admin's saved values don't silently revert to env/defaults on the
        # first read after this deploy. Falls to ``{}`` (env → hardcoded) if
        # neither shape is present.
        src = root if _looks_like_legacy_rag_root(root) else {}

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


# ── Agent-LLM eval settings (Level 2 — per-agent LLM output scoring) ──────
# Stored under ``eval_settings["llm_evals"]`` — sibling to
# ``eval_settings["rag_evals"]``. Each flavor owns an independent copy of
# every setting (including its own ``auto_run_enabled``) so a change to one
# never affects the other. Resolver falls back DB → env → hardcoded default
# per field, mirroring :func:`get_eval_settings` so downstream code never
# guards for missing values.

AGENT_LLM_EVAL_SETTINGS_KEYS: tuple[str, ...] = (
    "auto_run_enabled",
    "judge_model",
    "judge_engine",
    "metric_threshold",
    "metrics_enabled",
    "metric_thresholds",
)

# ``auto_run_enabled`` mirrors the RAG flavor: an unset env resolves to
# False directly (via ``_bool_env``). Kept as a named constant for
# documentation and to make a future ``_bool_env → Optional[bool]`` change
# trivial to wire in.
_DEFAULT_AGENT_LLM_AUTO_RUN_ENABLED = False
_DEFAULT_AGENT_LLM_JUDGE_MODEL = "gpt-4o"
# One deepeval runtime for both RAG and agent-LLM evals — falls back to the
# shared ``EVAL_JUDGE_ENGINE`` env, not a dedicated agent-LLM env, because
# there is no case for running one flavor on ``deepeval`` and the other on
# ``legacy`` simultaneously.
_DEFAULT_AGENT_LLM_JUDGE_ENGINE = "deepeval"
_DEFAULT_AGENT_LLM_METRIC_THRESHOLD = 0.7
_DEFAULT_AGENT_LLM_METRICS_ENABLED: tuple[str, ...] = (
    "correctness",
    "instruction_following",
    "persona_adherence",
)


@dataclass(frozen=True)
class AgentLlmEvalSettings:
    """Resolved per-org agent-LLM eval configuration. Immutable so callers
    can't mutate it accidentally when threading it through the eval pipeline.

    Every field has a value at construction time — the resolver
    (:func:`get_agent_llm_eval_settings`) walks the DB → env → hardcoded
    default chain per field, so ``AgentLlmEvalService`` and the run-eval
    Procrastinate task never need ``or DEFAULT`` fallbacks at the call site.
    """

    auto_run_enabled: bool
    judge_model: str
    judge_engine: str
    metric_threshold: float
    metrics_enabled: list[str] = field(default_factory=list)
    metric_thresholds: dict[str, float] = field(default_factory=dict)


def get_agent_llm_eval_settings(
    org_eval_settings: Optional[Mapping[str, Any]],
) -> AgentLlmEvalSettings:
    """Resolve the org's agent-LLM eval configuration with DB → env → hardcoded
    fallback.

    ``org_eval_settings`` is the raw ``organizations.eval_settings`` JSONB (or
    ``None``). Agent-LLM knobs live under the ``llm_evals`` sub-object; an
    org with no ``llm_evals`` slot still resolves via env → hardcoded default
    per field, so no explicit setup is needed for the eval flow to work.

    This is the ONE resolver — every caller that needs an agent-LLM eval knob
    (``AgentLlmEvalService.run_eval_for_agent``, judge factory, run-eval
    Procrastinate task) goes through it.
    """
    root: Mapping[str, Any] = org_eval_settings or {}
    sub_raw = root.get(LLM_EVAL_SLOT)
    if isinstance(sub_raw, Mapping):
        sub: Mapping[str, Any] = sub_raw
    else:
        # Back-compat: the pre-restructure shape used ``agent_llm`` as the
        # nested-slot name. Read from there so an admin's saved values keep
        # working until a fresh save from the FE lifts them into the
        # canonical ``llm_evals`` slot. Falls to ``{}`` when neither is set.
        legacy = root.get(_LEGACY_LLM_SLOT)
        sub = legacy if isinstance(legacy, Mapping) else {}

    # bool — same shape as RAG's ``auto_run_enabled``: DB overrides env when
    # the key is explicitly a bool; otherwise falls to env (which defaults
    # to False when unset). ``AGENT_LLM_EVAL_AUTO_RUN_ENABLED`` env is
    # optional (not in MANDATORY_KEYS); read via getattr so a not-yet-set
    # env var doesn't break older deployments that haven't restarted.
    if "auto_run_enabled" in sub and isinstance(sub["auto_run_enabled"], bool):
        auto_run_enabled = sub["auto_run_enabled"]
    else:
        auto_run_enabled = bool(
            getattr(env_settings, "AGENT_LLM_EVAL_AUTO_RUN_ENABLED", False)
        )

    judge_model = (
        _first_non_empty_str(
            sub.get("judge_model"),
            env_settings.AGENT_LLM_EVAL_JUDGE_MODEL,
        )
        or _DEFAULT_AGENT_LLM_JUDGE_MODEL
    )
    judge_engine = (
        _first_non_empty_str(
            sub.get("judge_engine"),
            env_settings.EVAL_JUDGE_ENGINE,
        )
        or _DEFAULT_AGENT_LLM_JUDGE_ENGINE
    )
    metric_threshold = (
        _first_valid_ratio(
            sub.get("metric_threshold"),
            env_settings.AGENT_LLM_EVAL_METRIC_THRESHOLD,
        )
        or _DEFAULT_AGENT_LLM_METRIC_THRESHOLD
    )
    metrics_enabled = (
        _first_non_empty_list(
            sub.get("metrics_enabled"),
            env_settings.AGENT_LLM_EVAL_METRICS_ENABLED,
        )
        or list(_DEFAULT_AGENT_LLM_METRICS_ENABLED)
    )

    raw_overrides = sub.get("metric_thresholds")
    metric_thresholds: dict[str, float] = {}
    if isinstance(raw_overrides, Mapping):
        for name, value in raw_overrides.items():
            if not isinstance(name, str) or not name.strip():
                continue
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)) and 0.0 < float(value) <= 1.0:
                metric_thresholds[name.strip()] = float(value)

    return AgentLlmEvalSettings(
        auto_run_enabled=auto_run_enabled,
        judge_model=judge_model,
        judge_engine=judge_engine,
        metric_threshold=metric_threshold,
        metrics_enabled=metrics_enabled,
        metric_thresholds=metric_thresholds,
    )


def load_agent_llm_eval_settings_for_org(db, org_id: Any) -> AgentLlmEvalSettings:
    """Convenience: fetch ``organizations.eval_settings`` for ``org_id`` and
    resolve the agent-LLM sub-object via :func:`get_agent_llm_eval_settings`.

    Same one-liner shape as :func:`load_eval_settings_for_org` so services,
    workers, and CLIs all read the same way.
    """
    from core.models.organization import Organization

    if org_id is None:
        return get_agent_llm_eval_settings(None)
    row = (
        db.query(Organization.eval_settings)
        .filter(Organization.id == org_id)
        .first()
    )
    return get_agent_llm_eval_settings(row[0] if row is not None else None)


# ── Call-transcript eval settings (Level 3 — post-call transcript scoring) ──
# Stored under ``eval_settings["call_evals"]`` — sibling to
# ``eval_settings["rag_evals"]`` and ``eval_settings["llm_evals"]``. Owns
# its own ``auto_run_enabled`` toggle so post-call scoring can be turned on
# without touching the RAG or agent-LLM flows. Resolver falls back DB → env
# → hardcoded default per field, mirroring the sibling resolvers so downstream
# code never guards for missing values.

CALL_EVAL_SLOT = "call_evals"

CALL_EVAL_SETTINGS_KEYS: tuple[str, ...] = (
    "auto_run_enabled",
    "judge_model",
    "judge_engine",
    "metric_threshold",
    "metrics_enabled",
    "metric_thresholds",
)

_DEFAULT_CALL_EVAL_AUTO_RUN_ENABLED = False
_DEFAULT_CALL_EVAL_JUDGE_MODEL = "gpt-4o"
_DEFAULT_CALL_EVAL_JUDGE_ENGINE = "deepeval"
_DEFAULT_CALL_EVAL_METRIC_THRESHOLD = 0.7
# Locked v1 metric set: 3 conversation-native + 2 single-turn safety
# (toxicity/bias) + 2 GEval system-prompt checks (instruction / persona).
# ``knowledge_retention`` is registered in the metric registry but stays
# OFF by default — it's a v2 candidate.
_DEFAULT_CALL_EVAL_METRICS_ENABLED: tuple[str, ...] = (
    "role_adherence",
    "conversation_completeness",
    "conversation_relevancy",
    "toxicity",
    "bias",
    "instruction_following",
    "persona_adherence",
)


@dataclass(frozen=True)
class CallEvalSettings:
    """Resolved per-org post-call transcript eval configuration. Immutable
    so callers can't mutate it accidentally when threading it through the
    eval pipeline.

    Every field has a value at construction time — the resolver
    (:func:`get_call_eval_settings`) walks the DB → env → hardcoded default
    chain per field, so ``CallTranscriptEvalService`` and the score-call
    Procrastinate task never need ``or DEFAULT`` fallbacks at the call site.
    """

    auto_run_enabled: bool
    judge_model: str
    judge_engine: str
    metric_threshold: float
    metrics_enabled: list[str] = field(default_factory=list)
    metric_thresholds: dict[str, float] = field(default_factory=dict)


def get_call_eval_settings(
    org_eval_settings: Optional[Mapping[str, Any]],
) -> CallEvalSettings:
    """Resolve the org's post-call transcript eval configuration with
    DB → env → hardcoded fallback.

    ``org_eval_settings`` is the raw ``organizations.eval_settings`` JSONB
    (or ``None``). Post-call knobs live under the ``call_evals`` sub-object;
    an org with no ``call_evals`` slot still resolves via env → hardcoded
    default per field, so no explicit setup is needed for the eval flow to
    work — except that ``auto_run_enabled`` defaults to False, so the FIRST
    thing an admin does to opt in is flip that toggle.

    This is the ONE resolver — every caller that needs a post-call transcript
    eval knob goes through it.
    """
    root: Mapping[str, Any] = org_eval_settings or {}
    sub_raw = root.get(CALL_EVAL_SLOT)
    sub: Mapping[str, Any] = sub_raw if isinstance(sub_raw, Mapping) else {}

    # bool — DB overrides env when the key is explicitly a bool; otherwise
    # falls to env (which defaults to False when unset).
    if "auto_run_enabled" in sub and isinstance(sub["auto_run_enabled"], bool):
        auto_run_enabled = sub["auto_run_enabled"]
    else:
        auto_run_enabled = bool(
            getattr(env_settings, "CALL_EVAL_AUTO_RUN_ENABLED", False)
        )

    judge_model = (
        _first_non_empty_str(
            sub.get("judge_model"),
            getattr(env_settings, "CALL_EVAL_JUDGE_MODEL", None),
        )
        or _DEFAULT_CALL_EVAL_JUDGE_MODEL
    )
    judge_engine = (
        _first_non_empty_str(
            sub.get("judge_engine"),
            env_settings.EVAL_JUDGE_ENGINE,
        )
        or _DEFAULT_CALL_EVAL_JUDGE_ENGINE
    )
    metric_threshold = (
        _first_valid_ratio(
            sub.get("metric_threshold"),
            getattr(env_settings, "CALL_EVAL_METRIC_THRESHOLD", None),
        )
        or _DEFAULT_CALL_EVAL_METRIC_THRESHOLD
    )
    metrics_enabled = (
        _first_non_empty_list(
            sub.get("metrics_enabled"),
            getattr(env_settings, "CALL_EVAL_METRICS_ENABLED", None),
        )
        or list(_DEFAULT_CALL_EVAL_METRICS_ENABLED)
    )

    raw_overrides = sub.get("metric_thresholds")
    metric_thresholds: dict[str, float] = {}
    if isinstance(raw_overrides, Mapping):
        for name, value in raw_overrides.items():
            if not isinstance(name, str) or not name.strip():
                continue
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)) and 0.0 < float(value) <= 1.0:
                metric_thresholds[name.strip()] = float(value)

    return CallEvalSettings(
        auto_run_enabled=auto_run_enabled,
        judge_model=judge_model,
        judge_engine=judge_engine,
        metric_threshold=metric_threshold,
        metrics_enabled=metrics_enabled,
        metric_thresholds=metric_thresholds,
    )


def load_call_eval_settings_for_org(db, org_id: Any) -> CallEvalSettings:
    """Convenience: fetch ``organizations.eval_settings`` for ``org_id`` and
    resolve the ``call_evals`` sub-object via :func:`get_call_eval_settings`.

    Same one-liner shape as :func:`load_eval_settings_for_org` /
    :func:`load_agent_llm_eval_settings_for_org` so services, workers, and
    CLIs all read the same way.
    """
    from core.models.organization import Organization

    if org_id is None:
        return get_call_eval_settings(None)
    row = (
        db.query(Organization.eval_settings)
        .filter(Organization.id == org_id)
        .first()
    )
    return get_call_eval_settings(row[0] if row is not None else None)
