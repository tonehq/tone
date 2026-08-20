"""Fixture package for the ``evals/`` dev harness scripts.

Split by eval type so each script imports only what it needs:
- ``tool_calls`` — MCP tool-selection fixtures (``ToolFixture`` + ``FIXTURES``)
  consumed by ``evals/tool_call_eval.py``.
- ``agent_llm_scenarios`` — per-agent LLM-output scenarios
  (``LLMScenario`` + ``SCENARIOS``) consumed by ``evals/agent_llm_eval.py``.

The tool-call names are re-exported from the package root so the pre-package
import ``from evals.fixtures import FIXTURES, ToolFixture`` keeps working
unchanged.
"""

from evals.fixtures.tool_calls import FIXTURES, ToolFixture

__all__ = ["FIXTURES", "ToolFixture"]
