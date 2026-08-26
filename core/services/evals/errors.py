class EvalError(Exception):
    """Base class for typed eval errors — mirrors ``RagError`` in the RAG
    service tree so callers can distinguish eval failures from platform errors."""


class EvalGenerationError(EvalError):
    """Question-generation LLM call failed or returned unparseable output."""


class EvalRunError(EvalError):
    """Retrieval / answer / judge failed while running an eval."""


class EvalNotFoundError(EvalError):
    """Eval row does not exist for the given upload / id."""


class EvalConfigurationError(EvalError):
    """Bad eval configuration — unknown metric name in EVAL_METRICS_ENABLED,
    unknown value for EVAL_JUDGE_ENGINE, etc. Raised at judge construction
    time so misconfiguration fails loudly before any expensive work."""


class InvalidEvalSettingsError(EvalError):
    """PUT /organizations/eval-settings received an invalid value — out-of-range
    threshold, non-positive top_k, unknown metric name, or malformed shape.
    The API layer maps this to HTTP 400; the service layer never raises
    HTTPException directly (transport-agnostic per backend coding standards)."""


class AgentLlmEvalError(EvalError):
    """Base class for typed per-agent LLM eval errors — separates the
    agent-LLM harness failures from the RAG eval flow so callers (CLI /
    future API adapter) can distinguish them cleanly."""


class AgentLlmEvalConfigError(AgentLlmEvalError):
    """Agent LLM eval could not be configured — unresolved agent, missing
    published config, unresolved provider key, or no scenarios matched. Raised
    BEFORE any LLM call so the caller aborts without persisting fake-FAIL rows."""


class AgentLlmEvalRunError(AgentLlmEvalError):
    """Agent LLM eval run itself failed mid-way — the LLM call raised, the
    judge orchestrator raised, or the persistence path raised. The run's
    completed scenarios are still persisted; this signals the batch was not
    a clean completion so the CLI exits non-zero."""


class AgentLlmScenarioNotFoundError(AgentLlmEvalError):
    """Requested scenario row does not exist for the caller's (agent, org)
    scope. Distinguished from a general 404 so the route layer can map it
    to a stable ``SCENARIO_NOT_FOUND`` error code the FE can react to."""


class AgentLlmEvalRunNotFoundError(AgentLlmEvalError):
    """Worker was asked to mark/complete/fail a ``run_id`` that isn't in
    ``agent_llm_eval_runs``. Should not happen on the happy path — the
    router inserts the pending row before enqueue — but can occur if
    Procrastinate replays a task after a partial deploy or after the row
    was manually deleted. Surfaces so the worker logs it clearly rather
    than crashing with a raw ``NoResultFound``."""


class AgentLlmScenarioKeyConflictError(AgentLlmEvalError):
    """Attempted to create / update a scenario whose ``scenario_key`` collides
    with another scenario on the SAME agent. Enforced via the
    ``uq_agent_llm_eval_scenarios_agent_key`` DB constraint AND explicitly
    checked at the service layer so we can surface the offending key to the
    user before the INSERT."""


class CallTranscriptEvalError(EvalError):
    """Base class for typed post-call transcript eval errors — separates the
    Level-3 (real-call) harness from the RAG and agent-LLM flows so callers
    (API adapter, worker task) can distinguish them cleanly."""


class CallTranscriptEvalConfigError(CallTranscriptEvalError):
    """Pre-run configuration error for a post-call transcript eval — missing
    ``agent_config`` on the call, missing provider key for the judge model,
    invalid metric name, etc. Raised BEFORE any LLM call so the Procrastinate
    task retries cleanly without persisting fake-FAIL rows."""
