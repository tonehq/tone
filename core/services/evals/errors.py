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
