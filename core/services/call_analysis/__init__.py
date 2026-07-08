"""STT-first analysis of finished calls (transcript + recording).

Reusable engine — the CLI (scripts/analyze_call.py) and the future post-call
worker both go through `analyze_call`.
"""

from core.services.call_analysis.analyzer import AnalysisOptions, analyze_call
from core.services.call_analysis.errors import (
    AnalysisError,
    CallAnalysisError,
    InputError,
    MissingKeyError,
)
from core.services.call_analysis.inputs import CallInputs, load_from_call_id, load_from_files
from core.services.call_analysis.schemas import AnalysisReport

__all__ = [
    "AnalysisOptions",
    "AnalysisReport",
    "AnalysisError",
    "CallAnalysisError",
    "CallInputs",
    "InputError",
    "MissingKeyError",
    "analyze_call",
    "load_from_call_id",
    "load_from_files",
]
