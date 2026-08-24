"""Category A — Agent-level content presence.

An agent must have *something* driving its conversation: either a non-empty
system prompt (``mode == "prompt"``) or an attached workflow (``mode ==
"workflow"``). Without one, the LLM has no instructions and the call fails
immediately at first turn. This is a hard blocker — no live probe can save a
prompt-less agent.

Kept in its own file (rather than folded into an existing checks module)
because it's the only rule that reads directly off ``AgentConfig`` columns
without touching any provider/leg/attachment. Adding future agent-level
content rules (e.g. required greeting on inbound) drops in here cleanly.
"""

from __future__ import annotations

from typing import ClassVar

from core.services.readiness.base import CheckContext, ShallowCheck
from core.services.readiness.schemas import (
    Category,
    CheckResult,
    ResourceRef,
    Severity,
)


class AgentPromptOrWorkflowPresentCheck(ShallowCheck):
    """Every agent needs a prompt (prompt-mode) or a workflow (workflow-mode)."""

    id: ClassVar[str] = "agent.prompt_or_workflow_present"
    category: ClassVar[Category] = Category.AGENT
    severity: ClassVar[Severity] = Severity.BLOCKER

    async def run(self, ctx: CheckContext) -> CheckResult:
        # No config resolved (brand-new agent, no versions yet). Every other
        # check will already fail; surface a specific message here rather
        # than crashing on attribute access.
        if ctx.config is None:
            return self._fail(
                "Agent has no configuration to check.",
                remediation="Create a config version for this agent first.",
            )

        # ``mode`` defaults to "prompt" via server_default (agent_config.py:27);
        # normalise to be defensive against legacy rows or manual DB edits.
        mode = (getattr(ctx.config, "mode", None) or "prompt").strip().lower()

        if mode == "workflow":
            if getattr(ctx.config, "workflow_id", None) is None:
                return self._fail(
                    "Workflow mode selected but no workflow is attached.",
                    remediation=(
                        "Attach a workflow in the agent editor, or switch back "
                        "to prompt mode and add a system prompt."
                    ),
                )
            return self._pass("Workflow attached — agent has conversation logic.")

        # Prompt mode (default). A whitespace-only string is treated as empty:
        # it flows to the LLM as an empty system prompt and fails identically.
        prompt = (getattr(ctx.config, "system_prompt_template", None) or "").strip()
        if not prompt:
            return self._fail(
                "System prompt is empty.",
                remediation=(
                    "Open the agent editor and add a system prompt, or switch "
                    "to workflow mode and attach a workflow."
                ),
            )
        return self._pass("System prompt present.")


class AgentWorkflowValidCheck(ShallowCheck):
    """When the agent is in workflow mode, its attached workflow must be valid.

    Only applies when ``mode == "workflow"`` AND a workflow is attached — the
    prompt/workflow presence check already flags missing workflows. We READ
    the ``WorkflowVersion.is_valid`` flag (computed at save time by the
    workflow service via ``validate_graph``); we do NOT re-run validation.
    The flag is the workflow layer's contract for "runnable"; readiness
    consumes it verbatim so the two subsystems can never disagree.
    """

    id: ClassVar[str] = "agent.workflow_valid"
    category: ClassVar[Category] = Category.AGENT
    severity: ClassVar[Severity] = Severity.BLOCKER

    def applies(self, ctx: CheckContext) -> bool:
        if ctx.config is None:
            return False
        mode = (getattr(ctx.config, "mode", None) or "prompt").strip().lower()
        return mode == "workflow" and getattr(ctx.config, "workflow_id", None) is not None

    def skip_reason(self, ctx: CheckContext) -> str:
        if ctx.config is None:
            return "No agent config to check."
        mode = (getattr(ctx.config, "mode", None) or "prompt").strip().lower()
        if mode != "workflow":
            return "Agent is in prompt mode — workflow check not required."
        return "No workflow attached (see prompt-or-workflow check)."

    async def run(self, ctx: CheckContext) -> CheckResult:
        from core.models.workflow import Workflow

        workflow_id = ctx.config.workflow_id
        # Org-scope the lookup even though config.workflow_id is set by trusted
        # code paths: Workflow is an OrgScopedModel and defense-in-depth means
        # readiness never reads a workflow row from a different tenant, even if
        # the FK ever points at a cross-org id (data-migration bug, direct DB
        # edit). Prevents IDOR-style existence leaks via readiness.
        workflow = (
            ctx.db.query(Workflow)
            .filter(
                Workflow.id == workflow_id,
                Workflow.organization_id == ctx.org_id,
                Workflow.deleted_at.is_(None),
            )
            .first()
        )
        if workflow is None:
            return self._fail(
                "Attached workflow no longer exists.",
                remediation=(
                    "Attach a different workflow or switch to prompt mode."
                ),
                resource_ref=ResourceRef(type="workflow", id=str(workflow_id)),
            )

        # ``draft_version`` is the single runnable graph — there is no separate
        # published version (see workflow.py:54-61 comment). Missing means the
        # workflow was created but never saved a graph.
        version = workflow.draft_version
        if version is None:
            return self._fail(
                f"Workflow '{workflow.name}' has no version to run.",
                remediation="Open the workflow editor and save a graph.",
                resource_ref=ResourceRef(type="workflow", id=str(workflow.id)),
            )

        if not getattr(version, "is_valid", False):
            errors = getattr(version, "validation_errors", None) or []
            preview_parts = []
            for err in errors[:2]:
                if isinstance(err, dict):
                    node = err.get("node_name") or err.get("code") or "workflow"
                    message = err.get("message") or "invalid"
                    preview_parts.append(f"{node}: {message}")
                else:
                    preview_parts.append(str(err))
            more = f" +{len(errors) - 2} more" if len(errors) > 2 else ""
            preview = "; ".join(preview_parts) if preview_parts else "no details available"
            return self._fail(
                f"Workflow '{workflow.name}' is invalid: {preview}{more}.",
                remediation=(
                    "Open the workflow editor and fix the flagged nodes."
                ),
                resource_ref=ResourceRef(type="workflow", id=str(workflow.id)),
            )
        return self._pass(f"Workflow '{workflow.name}' is valid.")


# Scheduled-call statuses that count as "work in flight" for an outbound
# agent. Anything terminal (completed/failed/canceled/no_answer/busy) is
# excluded — a healthy agent that finished its queue should still surface
# the warning so users know they need to enqueue more work.
#
# The active states (``processing/dispatched/in_progress``) are owned by
# ``outbound_call_service._ACTIVE_OUTBOUND_STATES`` — we reuse that constant
# so future runtime additions (e.g. a new intermediate state) flow through to
# readiness automatically. Only the "queued but not yet running" bucket
# (``scheduled``) is added here, since that's the readiness-specific concept
# of "has work" the outbound-runtime constant doesn't need to model.


def _outbound_pending_statuses() -> tuple[str, ...]:
    """Return the tuple of scheduled-call statuses that count as pending work.

    Wrapped in a function so the outbound-service import stays lazy (avoids
    circular-import risk at module load).
    """
    from core.services.outbound_call_service import _ACTIVE_OUTBOUND_STATES

    return ("scheduled",) + tuple(_ACTIVE_OUTBOUND_STATES)


class AgentOutboundHasWorkCheck(ShallowCheck):
    """Outbound agents need something to dial — contacts or scheduled calls.

    A common support pattern: user configures an outbound agent perfectly
    (LLM/STT/TTS/prompt/phone) and publishes it, then wonders why nothing
    happens. Answer: no contacts assigned and no calls scheduled. The
    system has no way to know WHO to call.

    ``WARNING`` severity (not blocker): some workflows publish the agent
    first and enqueue work via API later, which is legitimate. The drawer
    surfaces the "nothing to do" state so users notice immediately without
    blocking a valid publish.
    """

    id: ClassVar[str] = "agent.outbound_has_work"
    category: ClassVar[Category] = Category.AGENT
    severity: ClassVar[Severity] = Severity.WARNING

    def applies(self, ctx: CheckContext) -> bool:
        agent_type = (getattr(ctx.agent, "agent_type", None) or "").lower()
        return agent_type in {"outbound", "both"}

    def skip_reason(self, ctx: CheckContext) -> str:
        return "Inbound-only agent — no outbound work required."

    async def run(self, ctx: CheckContext) -> CheckResult:
        from core.models.agent_contact import AgentContact
        from core.models.scheduled_call import ScheduledCall

        agent_id = ctx.agent.id
        contact_count = (
            ctx.db.query(AgentContact)
            .filter(AgentContact.agent_id == agent_id)
            .count()
        )
        pending_call_count = (
            ctx.db.query(ScheduledCall)
            .filter(
                ScheduledCall.agent_id == agent_id,
                ScheduledCall.status.in_(_outbound_pending_statuses()),
            )
            .count()
        )

        if contact_count == 0 and pending_call_count == 0:
            return self._fail(
                "Outbound agent has no assigned contacts and no scheduled "
                "calls — it won't dial anyone until you give it work.",
                remediation=(
                    "Assign contacts to this agent, or schedule outbound "
                    "calls via the campaign / API."
                ),
            )
        parts = []
        if contact_count:
            parts.append(f"{contact_count} contact(s) assigned")
        if pending_call_count:
            parts.append(f"{pending_call_count} call(s) pending")
        return self._pass(f"Outbound agent has work: {', '.join(parts)}.")
