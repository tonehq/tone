"""Exceptions for the call-analysis engine."""


class CallAnalysisError(Exception):
    """Base class for all call-analysis errors."""


class InputError(CallAnalysisError):
    """Invalid or missing input (audio file, transcript, call record)."""


class MissingKeyError(CallAnalysisError):
    """A required provider API key is not configured."""


class AnalysisError(CallAnalysisError):
    """A fatal failure in the analysis pipeline (e.g. STT failed)."""
