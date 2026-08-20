"""Per-agent LLM eval harness — dev/QA scoring of an agent's LLM output
against a fixture set of scenarios, keyed on the agent's actual DB config.

Transport-agnostic: the service ``AgentLlmEvalService`` takes a SQLAlchemy
session + plain args and returns dataclass summaries. The CLI wrapper
(``evals/agent_llm_eval.py``) is a thin adapter; a FastAPI adapter can be
added later without touching the service.

Reuses ``core/services/evals/deepeval/`` (telemetry, ``ToneDeepEvalLLM``
adapter, ``metric_registry``) — the same DeepEval foundation the RAG judge
uses. New per-agent metrics (``bias``, ``toxicity``, ``persona_adherence``,
``instruction_following``) are registered there so both eval flows share one
supported-metrics catalog.
"""

from core.services.evals.agent_llm.service import (
    AgentLlmEvalService,
    AgentLlmRunSummary,
)

__all__ = ["AgentLlmEvalService", "AgentLlmRunSummary"]
