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
