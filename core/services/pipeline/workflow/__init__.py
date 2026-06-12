"""Call-time workflow runtime — graph traversal engine for ``mode == "workflow"`` agents.

This subpackage is **framework-agnostic and pure** (no Pipecat imports) so it can be
unit-tested in isolation and wired into the Pipecat runner separately. The
:class:`WorkflowEngine` consumes the canonical graph (as stored in
``workflow_versions.graph``) plus a per-call :class:`WorkflowCallContext` and emits
:class:`NodeDirective` objects the runner applies to the live LLM/TTS pipeline.

Integration seam (kept out of this package so the live pipeline is never touched until
the runner is implemented):

* ``service_resolver.load_agent_service_config`` — when ``config.mode == "workflow"``,
  load the agent's assigned workflow's published graph and embed it as
  ``result["workflow"]`` (+ bump the cache version).
* ``pipeline/params/base.py`` — carry ``workflow`` + expose ``is_workflow``.
* ``bot.run_bot`` — select a ``WorkflowPipelineRunner`` when ``params.is_workflow``.

Until the runner is wired, ``mode == "workflow"`` agents resolve and run exactly like
``prompt`` mode (the resolver simply ignores the workflow), so existing calls are
unaffected.
"""
from core.services.pipeline.workflow.context import WorkflowCallContext  # noqa: F401
from core.services.pipeline.workflow.engine import NodeDirective, WorkflowEngine  # noqa: F401
from core.services.pipeline.workflow.graph import WorkflowGraphRuntime  # noqa: F401
