class EvalError(Exception):
    """Base class for typed eval errors — mirrors ``RagError`` in the RAG
    service tree so callers can distinguish eval failures from platform errors."""


class EvalGenerationError(EvalError):
    """Question-generation LLM call failed or returned unparseable output."""


class EvalRunError(EvalError):
    """Retrieval / answer / judge failed while running an eval."""


class EvalNotFoundError(EvalError):
    """Eval row does not exist for the given upload / id."""
