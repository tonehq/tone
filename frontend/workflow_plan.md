
---

## Implementation Status (delivered)

**Backend — builder (complete, compiles):**
- Models `core/models/workflow.py` (`Workflow`, `WorkflowVersion`); `agent_configs.mode` + `workflow_id` added; enums `WorkflowNodeType`/`EdgeConditionType`/`AgentConfigMode`.
- Alembic migration `alembic/versions/d4f7a1c9e2b8_add_workflows.py` (additive; head was `a4e21c9b3d7f`).
- `core/services/workflow/` — `schema.py` (canonical graph Pydantic + `validate_graph`), `service.py` (`WorkflowService`: list/create/get/save_draft/validate/publish/list_versions/delete/import_vapi/export_vapi), `vapi_adapter.py`.
- API `core/api/v1/workflows.py` registered under `/workflow` in `main.py` (core + EE).
- Assignment wired through the existing agent path (`AgentConfigRequest.mode/workflow_id` → `AgentService._CONFIG_FIELDS`).

**Backend — runtime engine core (complete + unit-tested, pure):** `core/services/pipeline/workflow/` — `context.py`, `graph.py`, `conditions.py` (safe AST logic eval), `engine.py` (`WorkflowEngine` + `NodeDirective`). Functionally tested: logic/AI edge routing, decision-node settling, transfer/end directives, `{{var}}` substitution, global-node interrupts.
- **Pending integration seam (not wired, by design):** `service_resolver` / `params/base` / `bot.py` / a `WorkflowPipelineRunner` that injects the LLM-backed navigator+extractor and mutates the live Pipecat `LLMContext`. Until wired, `mode=='workflow'` agents fall back to prompt mode → existing calls are byte-identical and unaffected. This step needs the running Pipecat stack to validate.

**Frontend — full editor (complete, type-clean, lint-clean, `yarn build` passes):**
- Standalone **Workflows** feature under `frontend/src/components/workflows/` — `WorkflowListPage`, `CreateWorkflowModal`, `WorkflowBuilder` (React Flow canvas), `WorkflowToolbar`, `NodePalette`, `NodeConfigDrawer`, `canvas/nodes/*` (BaseNode + per-type), `canvas/edges/ConditionEdge`, `nodeRegistry.ts`.
- Data layer: `types/workflow.ts`, `services/workflowService.ts`, `atoms/WorkflowAtom.tsx`, `utils/workflowGraphUtils.ts` (+ Vapi `fromVapi`).
- Routes `app/(dashboard)/workflows/page.tsx` + `[id]/page.tsx` (full-screen, `next/dynamic ssr:false`); sidebar "Workflows" nav; focused-route predicate; scoped React-Flow theming in `globals.css`.
- Modern design system applied (indigo/slate tokens, mono technical labels, per-type accents, AI/Logic edges, framer-motion, dark mode, a11y).
- **Pending:** the per-agent assignment control inside the agent editor (`WorkflowAssignStep`) — backend supports it now via `update_agent` (`config.mode` + `config.workflow_id`); the small UI control is a follow-up.
