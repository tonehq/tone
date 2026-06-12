# Plan: Agent Workflows / Pathways (Bland AI–style visual conversation builder)

## Context

Tone agents today are **stateless**: a single `system_prompt_template` + `first_message` drives one LLM loop for the whole call (`core/services/pipeline/`). The user wants a **node-based visual conversation flow builder** (like Bland AI "Pathways" / Conversational Pathways) so an agent's behavior can branch across discrete conversation stages, extract variables, call tools/webhooks, transfer, and end — all designed on a visual canvas.

Key product decisions (confirmed with user):
- **Full end-to-end**: visual builder UI + DB + API + a working **call-time runtime engine** that traverses the graph during live calls.
- **Workflows are a standalone, org-level entity** — **create / list / edit happen OUTSIDE the agent**, on their own top-level **"Workflows"** page (like Agents, Tools, Knowledge Base). A workflow is reusable and not owned by any single agent.
- **Only the *assignment* lives inside the agent config**: `AgentConfig.workflow_id` selects which workflow that agent runs. One workflow per agent at a time (it's a single column on the live config); the same workflow can be reused across many agents.
- **Drafts + published**: each workflow has a draft working copy plus a published-version history; **only a published, valid workflow can be assigned** to an agent.
- **Prompt + workflow are LAYERED, not either/or** (confirmed by deep research on Bland & Vapi — see "Prompt layering" below). The agent's existing system prompt is the **global persona layer** (identity, tone, call-wide rules) and stays in effect *even when a workflow is assigned*. The workflow adds an optional **workflow-level global prompt** (Bland's "Add Global Prompt to All Nodes") plus **per-node prompts** (what to do at each stage). At each conversation node the runtime composes: `agent persona prompt` + `workflow global prompt` + `node prompt`.
- **`AgentConfig.mode` chooses the conversation-flow driver**, not whether the prompt is used: `'prompt'` (single-prompt assistant — today's behavior) vs `'workflow'` (the assigned graph drives turn-to-turn flow, with the persona prompt layered into every node). Existing agents default to `'prompt'` → zero behavior change.
- **Frontend canvas** uses **React Flow** (`@xyflow/react` v12, https://reactflow.dev/). The agent editor only gets a small **assignment control** (flow-driver toggle + workflow dropdown), not the canvas.
- **Backend** mirrors the `core/services/pipeline/` builder/runner separation.

### v1 runtime node set (editor UI shows all; these execute at call time)
Start, Conversation/Default, Knowledge Base, Transfer Call, End Call, Webhook, Wait for Response, **Tool Call, MCP Call, Custom Tool Call**.
Phase-2 nodes (editor-only in v1): Transfer Pathway, Press Button/Route (DTMF), SMS, Global Nodes.

---

## Architecture overview

```
STANDALONE "Workflows" page (top-level, org-level)
  WorkflowList → create / edit
       └─ open one → React Flow canvas ──save DRAFT graph JSON──> POST /workflow/save_draft
                                                                   → publish
DB: workflows (container: org-level, name, status, published/draft version pointers)
    workflow_versions (draft + published graph JSONB snapshots)

AGENT EDITOR (config section)
  Assignment control: mode toggle + "Assign workflow" dropdown (published workflows)
       └─ sets AgentConfig.mode='workflow' + AgentConfig.workflow_id = <id>

CALL TIME: bot.run_bot → params.load (mode==workflow)
  → AgentConfig.workflow_id → workflow.published_version_id → graph
  → WorkflowPipelineRunner (subclass of PipecatPipelineRunner)
      → WorkflowEngine state machine (current node, variables, history)
          → navigator (one structured LLM call: extract vars + pick next edge)
          → node handlers (conversation/webhook/tool/mcp/transfer/end/KB)
```

The STT→LLM→TTS Pipecat pipeline is **unchanged**; workflow mode only changes *how the LLM context/system-prompt is driven between turns* and which tools are registered per node.

### Prompt layering (research-backed)

Deep research on Bland.ai Conversational Pathways and Vapi.ai (primary docs) found that a global/persona prompt and node prompts are **used together, never a mutually-exclusive toggle**:
- **Bland** ships *"Add Global Prompt to All Nodes"* — persona/tone/call-handling applied to every node *in addition to* each node's own Prompt (or Static Text). Division of labor: **global = personality / how to communicate**, **per-node = what to do at this stage**.
- **Vapi** single-prompt Assistants pack persona (section 1) + workflow "playbook" (section 5) into one structured system prompt; its node Workflows give each node its own prompt. (Vapi now steers new builds to Assistants/Squads over Workflows.)
- **Cross-vendor best practice** (Bland, Vapi, Dograh): a **global persona layer** for identity/tone/call-wide rules + **per-node prompts** that scope behavior to each stage — the global layer frames every node. Exact string-merge order is not published by either vendor; we define ours explicitly:

**Tone's composition at each conversation node** (built in the node handler, then variable-substituted):
```
[ AgentConfig.system_prompt_template ]      ← agent persona (global, always)
+ [ graph.globalPrompt (optional) ]          ← workflow-wide instructions (Vapi globalPrompt / "apply to all nodes")
+ [ node.prompt ]                             ← stage-specific instructions (per Vapi conversation node)
```
Guardrails/safety lines (if any) are appended last so they take precedence. The persona/global layers are identical every turn (prompt-cache friendly); only the node layer changes as the call traverses the graph.

---

## DATABASE SCHEMA DESIGN (detailed)

### Design decision: store the graph as one JSONB column (not normalized node/edge tables)

Two options were considered:

**Graph format = React-Flow-native canonical, Vapi-compatible.** We persist a graph React Flow can render with **no transform** — nodes `{id, type, position, data}`, edges `{id, source, target, data}` — and we put the **Vapi field set inside each node's `data`** (`name, isStart, prompt, messagePlan, variableExtractionPlan, toolId/tool, …`) and the edge `condition` inside `edge.data`. Top-level `globalPrompt` + `artifactPlan` are kept as Vapi names. A thin **Vapi import/export converter** maps this ↔ the pure Vapi shape (the user's file) on demand. This gives both: the canvas renders the stored graph directly, and we stay Vapi-compatible. (See the side-by-side example below.)

| Option | How | Verdict |
|---|---|---|
| **A. Single JSONB graph, React-Flow-native (Vapi fields in `data`)** (chosen) | One `workflow_versions` row holds `{nodes, edges, globalPrompt, artifactPlan}` in a `graph JSONB` column | ✅ Editor renders it with zero transform; runtime loads it once per call into a dict keyed by node `id` (== Vapi name) for O(1) lookups; versioning = one row copy; Vapi import/export via a thin converter; matches the existing `AgentConfig.*_settings` JSONB convention |
| **B. Normalized** `workflow_nodes` + `workflow_edges` tables | One row per node and per edge | ❌ N+1 reads to reassemble the graph; deep-copy of all child rows per version; the runtime never needs relational queries over nodes |

Trade-off accepted: no DB-level FK integrity *between* edges and nodes. Mitigated by **service-layer validation** on every save/publish (exactly one `isStart`, edges reference existing node names, no orphan/unreachable nodes) + a `graph_checksum` for optimistic concurrency. A GIN index on `graph` still answers rare admin queries ("which workflows use a transferCall node").

### Core requirement: workflows are standalone (org-level); the agent config only *points* at one

- A **workflow** is an **org-level entity**, created/listed/edited on its own top-level page — it is **not owned by an agent**.
- Each workflow has its own **draft** working copy plus a history of **published versions** — edit the draft freely without touching what's live.
- An agent's **live `AgentConfig`** carries a single `workflow_id` (the assigned workflow) + a `mode` toggle. Because a config has exactly one `workflow_id`, an agent runs **one workflow at a time**. The same workflow can be **reused across many agents**.
- Only a **published, valid** workflow may be assigned.

This needs **two tables** (workflow container + version snapshots) + **two columns on `agent_configs`**:

### Entity relationships

```
organizations
   │ 1
   │ *  (organization_id — plain UUID scope, per OrgScopedModel)
workflows  (org-level container: name, status, version pointers)   ← NOT linked to any agent
   │ 1
   │ * published_version_id ─┐  draft_version_id ─┐   (FKs → workflow_versions, SET NULL, use_alter)
   ▼                         ▼                     ▼
workflow_versions  (graph snapshots + the editable draft)
   └─ graph JSONB = { nodes:[...], edges:[...], globalPrompt }   ← React-Flow-native (Vapi fields in node.data)
        (per-node variableExtractionPlan handles all extraction — NO separate extraction-schema table)

agents ──1───< agent_configs   (existing; versioned: UNIQUE(agent_id, version))
                     │
                     ├─ mode = 'prompt' | 'workflow'           ← per-agent toggle (NEW column)
                     └─ workflow_id ──FK──> workflows.id        ← the ASSIGNED workflow (NEW column)

Runtime read path (call time):
  Agent.published_config_id → AgentConfig(mode=='workflow', workflow_id)
    → workflows.published_version_id → workflow_versions.graph
    → WorkflowEngine (in-memory)
```

The editor always edits the **draft** version; **Publish** snapshots the draft into a new published version; **Assign** (in the agent editor) writes `AgentConfig.workflow_id` + `mode='workflow'`.

> **Naming:** these are top-level tables `workflows` / `workflow_versions` (model `Workflow` / `WorkflowVersion`), not `agent_workflows`, to reflect that they are standalone and agent-independent.

### Table 1: `workflows` (org-level container — new `core/models/workflow.py`, extends `OrgScopedModel`)

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | UUID | no | `uuid4` | PK |
| `organization_id` | UUID | no | `get_current_org_id` | indexed; tenant scope (the ONLY ownership — no `agent_id`) |
| `name` | String(200) | no | — | workflow name (e.g. "Inbound triage") |
| `description` | String(500) | yes | — | optional |
| `status` | String(16) | no | `'draft'` | `'draft'` \| `'published'` — has it ever been published? |
| `published_version_id` | UUID | yes | `NULL` | **FK → `workflow_versions.id` SET NULL, use_alter** — the live snapshot used when assigned |
| `draft_version_id` | UUID | yes | `NULL` | **FK → `workflow_versions.id` SET NULL, use_alter** — the current editable draft |
| `latest_version` | Integer | no | `0` | high-water mark for version numbering |
| `created_by_user_id` | UUID | no | — | FK → `users.id` |
| `created_at` / `updated_at` | DateTime(tz) | no | now/onupdate | from `TimestampModel` |
| `deleted_at` / `archived_at` | DateTime(tz) | yes | — | soft-delete |

**Constraints & indexes**
- `UniqueConstraint(organization_id, name)` → `uq_workflows_org_name` (names unique per org; mirrors `uq_agents_org_name`).
- `Index(ix_workflows_organization_id)`.

### Table 2: `workflow_versions` (graph snapshots + draft — same model file)

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | UUID | no | `uuid4` | PK |
| `organization_id` | UUID | no | `get_current_org_id` | tenant scope |
| `workflow_id` | UUID | no | — | **FK → `workflows.id` ON DELETE CASCADE**; indexed |
| `version` | Integer | no | — | sequential per workflow |
| `is_draft` | Boolean | no | `true` | `true` = the unpublished working copy; `false` = an immutable published snapshot |
| `graph` | JSONB | no | `'{"nodes":[],"edges":[],"globalPrompt":""}'` | **React-Flow-native graph, Vapi fields in `node.data`** (shape below); GIN-indexed |
| `start_node_name` | String(120) | yes | — | denormalized name of the `isStart:true` node (validated to exist) |
| `graph_checksum` | String(64) | yes | — | sha256 of canonical graph → optimistic-concurrency guard on draft saves |
| `is_valid` | Boolean | no | `false` | last validation result |
| `validation_errors` | JSONB | yes | — | `[{code, node_name, message}]` |
| `published_at` | DateTime(tz) | yes | — | set when this snapshot is published |
| `created_by_user_id` | UUID | no | — | FK → `users.id` |
| `created_at` / `updated_at` | DateTime(tz) | no | now/onupdate | from `TimestampModel` |
| `deleted_at` | DateTime(tz) | yes | — | soft-delete |

**Constraints & indexes**
- `UniqueConstraint(workflow_id, version)` → `uq_workflow_versions_workflow_version`.
- `Index(ix_workflow_versions_workflow_id)`, GIN index on `graph`.

> **Lifecycle in practice:** Creating a workflow (on the standalone page) inserts a `workflows` row + one `workflow_versions` draft (`version=1, is_draft=true`, just a Start node), `draft_version_id` → it. Editing the canvas saves into that draft row (checksum-guarded). **Publish** clones the draft into a new `is_draft=false` snapshot, sets `published_version_id`, `published_at`, `status='published'`, and starts a fresh draft. **Assign** happens in the *agent* editor: it writes `AgentConfig.workflow_id` + `mode='workflow'` (requires the workflow to have a `published_version_id`).

> **No separate extraction-schema table.** All variable extraction is **per-node** via `data.variableExtractionPlan.output[]` (stored in the graph, versions with it) — that fully covers v1. A *call-wide* reusable extraction schema (Vapi's `artifactPlan.structuredOutputIds`) is a **phase-2** nicety; if/when needed it is stored **inline in `graph.artifactPlan`** (so it still versions with the draft) — no extra table, no FK, until cross-workflow reuse is actually required.

### Changes to `agent_configs` (edit `core/models/agent_config.py`) — the assignment lives HERE

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `mode` | String(16) | no | `'prompt'` | `'prompt'` \| `'workflow'` — chooses the **conversation-flow driver** (single prompt vs assigned graph). Existing rows default to `'prompt'` → zero behavior change |
| `workflow_id` | UUID | yes | `NULL` | **FK → `workflows.id` ON DELETE SET NULL** — the **assigned** workflow for this config version. One per config ⇒ one per agent at a time. `SET NULL` so deleting a workflow safely un-assigns it (and the resolver falls back to prompt mode) |

> The existing **`agent_configs.system_prompt_template`** is reused as the **global persona layer** and is applied in *both* modes — no new column needed for persona. In workflow mode it is layered above the workflow's `globalPrompt` (top-level graph field, Vapi-style) and each node's prompt (see **Prompt layering**).

### `graph` JSONB shape — **canonical = React-Flow-native, with Vapi fields inside `data`**

> **Can we send the Vapi JSON straight to React Flow? — No, not unmodified.** React Flow has hard structural requirements that the raw Vapi shape doesn't meet:
> | React Flow needs | Raw Vapi has | Fix |
> |---|---|---|
> | node `id` (string, unique) | `name` | `id = name` |
> | node **top-level** `position:{x,y}` | `metadata.position` | lift to top level |
> | node `data` object (custom node reads `data.*`) | fields at node top level (`prompt`, `model`…) | nest under `data` |
> | edge `id` (unique) | — (none) | generate `id = "${from}->${to}"` |
> | edge `source` / `target` | `from` / `to` | rename |
>
> So we **store the canonical shape as React-Flow-native** (zero transform to render) and keep the **Vapi fields inside each node's `data`**. A thin converter handles **Vapi import/export** only. This gives both: React Flow renders the stored graph directly, and we stay Vapi-compatible.

```jsonc
{
  "schemaVersion": 1,                        // forward-compat: migrate older graphs on read
  "nodes": [
    {
      "id": "introduction",                 // React Flow id  (== Vapi name)
      "type": "conversation",               // React Flow node type → custom component + Vapi type
      "position": { "x": 700, "y": -40 },   // React Flow reads this (top-level)
      "data": {                             // everything our node component + runtime needs (Vapi fields)
        "name": "introduction",
        "isStart": true,
        "prompt": "You are Alex... identify intent.",   // LLM (provider/model/temp) comes from the agent's AgentConfig.llm_settings — NO per-node model
        "messagePlan": { "firstMessage": "Hi! This is Alex from The Dine Spot. How may I help?" },
        "variableExtractionPlan": { "output": [ { "title": "user_intent", "type": "string", "enum": [], "description": "new/modify/cancel" } ] },
        "toolIds": []
      }
    }
  ],
  "edges": [
    {
      "id": "introduction->get_name",       // React Flow edge id (unique)
      "source": "introduction",             // React Flow source (== Vapi from)
      "target": "get_name",                 // React Flow target (== Vapi to)
      "type": "condition",                  // custom edge component (shows AI/Logic + label)
      "data": { "condition": { "type": "ai", "prompt": "user_intent contains \"new\" or booking a table" } }
    },
    {
      "id": "confirm_booking->book_table",
      "source": "confirm_booking", "target": "book_table", "type": "condition",
      "data": { "condition": { "type": "logic", "prompt": "{{ user_confirmed == true and number_of_guests <= 10 }}" } }
    }
  ],
  "globalPrompt": "You are upbeat and concise. Always confirm details back to the caller.",
  "artifactPlan": null   // optional, PHASE 2 — call-end extraction schemas stored INLINE here; no table in v1
}
```

**Edge / condition semantics** (condition lives in `edge.data.condition`, Vapi-compatible):
- `condition.type = "ai"` → navigator asks the LLM whether `prompt` (plain language) is satisfied. Empty `prompt` = unconditional (auto-advance).
- `condition.type = "logic"` → evaluated deterministically in Python as a LiquidJS boolean over the variable context (e.g. `{{ city == "San Francisco" }}`). No LLM call.
- Outgoing edges evaluated in order; first satisfied wins; `logic` checked before `ai`.

**Vapi import/export converter** (`workflowGraphUtils.ts` + a backend mirror): `fromVapi(node)` → `{id:name, type, position:metadata.position, data:{...rest}}`, `toVapi(node)` → `{name:id, type, metadata:{position}, ...data}`; edges `from/to ↔ source/target`, `condition ↔ data.condition`. Used at "Import Vapi JSON" / "Export" only — **not** on normal load/save.

### Node types (Vapi format) — full field set + example for EVERY type

Vapi's confirmed node types are `conversation`, `tool` (a `toolId` reference OR an inline `tool:{type}` built-in), `transferCall`, `endCall`, and the **global** variant (a `conversation` node with `isGlobal:true` + a `condition`). We adopt these verbatim and **add a `decision` node** — a pure router with no prompt that immediately evaluates its outgoing edge conditions (Vapi normally branches on edges; the decision node makes a branch point explicit on the canvas).

The examples below show each node type's **Vapi field set** (this is also the export shape). In the **stored canonical graph** these fields live inside the node's `data` object, with `id`/`type`/`position` lifted to the top level for React Flow (see the shape above). The **start** node is any node with `isStart:true` (typically the first `conversation`).

```jsonc
// ── conversation (the workhorse: talk + extract variables) ──────────────────
{
  "name": "introduction",
  "type": "conversation",
  "isStart": true,                                  // marks the entry node
  "prompt": "You are Alex, a calm booking assistant. Identify the caller's intent.",
  // no per-node model — the assigned agent's AgentConfig.llm_settings drives every node
  "messagePlan": { "firstMessage": "Hi! This is Alex from The Dine Spot. How may I help?" },
  "variableExtractionPlan": {
    "output": [
      { "title": "user_intent", "type": "string", "enum": [], "description": "new / modify / cancel" }
    ]
  },
  "toolIds": [],                                    // optional tools available during this node
  "metadata": { "position": { "x": 700, "y": -40 } }
}

// ── decision (OUR addition: pure router, no speech; routes via outgoing edges) ─
{
  "name": "route_by_intent",
  "type": "decision",
  "prompt": "Choose the branch that matches user_intent.",  // guidance for any "ai" edges; no firstMessage
  "metadata": { "position": { "x": 700, "y": 200 } }
  // Outgoing edges carry the conditions (logic or ai); on entry the engine evaluates them and jumps.
}

// ── tool: reference to an existing Tool row (webhook / custom / MCP / built-in) ─
{
  "name": "book_table",
  "type": "tool",
  "toolId": "b98fb5c6-9852-4012-b54e-d134de927e62",   // → tools.id (encodes webhook/custom/MCP config)
  "metadata": { "position": { "x": 264, "y": 3070 } }
}

// ── tool: inline built-in (endCall) — Vapi's hangup pattern ─────────────────
{
  "name": "hangup_after_booking",
  "type": "tool",
  "tool": { "type": "endCall" },
  "metadata": { "position": { "x": 482, "y": 3304 } }
}

// ── transferCall ────────────────────────────────────────────────────────────
{
  "name": "to_human",
  "type": "transferCall",
  "destination": { "type": "number", "number": "+15551234567" },
  "transferPlan": { "mode": "warm-transfer-say-summary" },
  "messagePlan": { "firstMessage": "Connecting you to a teammate now." },
  "metadata": { "position": { "x": 1100, "y": 1870 } }
}

// ── endCall ─────────────────────────────────────────────────────────────────
{
  "name": "goodbye",
  "type": "endCall",
  "messagePlan": { "firstMessage": "Thanks for calling The Dine Spot. Goodbye!" },
  "metadata": { "position": { "x": 482, "y": 3304 } }
}

// ── global node (conversation reachable from anywhere when its condition fires) ─
{
  "name": "human_handoff",
  "type": "conversation",
  "isGlobal": true,
  "condition": "{{ wants_human == true }}",          // Enter Condition (Liquid) — routable from any node
  "prompt": "Apologize and hand off to a human.",
  "messagePlan": { "firstMessage": "Of course — let me get a teammate." },
  "metadata": { "position": { "x": 1900, "y": 100 } }
}
```

**Mapping our earlier feature set onto Vapi's node model** (so nothing is lost): Knowledge Base → a `conversation` node with KB tools in `toolIds` (or a `knowledgeBaseId`); Webhook / Tool Call / MCP Call / Custom Tool → a `tool` node whose `toolId` points at the existing `Tool` row (the `Tool` model already encodes webhook/custom/MCP/built-in); Wait-for-response → a `conversation` node (no separate type); SMS → `tool` node with the SMS built-in tool. This keeps the persisted graph 1:1 with Vapi while reusing Tone's existing `Tool` infrastructure.

**Variables** use LiquidJS `{{ }}` syntax in prompts/firstMessages/conditions, e.g. `firstMessage: "A table for {{number_of_guests}} on {{reservation_date}} at {{reservation_time}} under {{customer_name}}. Correct?"`. Built-ins available at runtime: `{{now}}`, `{{date}}`, `{{customer.number}}`, `{{call.id}}` (resolver seeds these via `build_call_context`).

### Why this structure handles all cases (the part that actually matters)

The wire shape is secondary; robustness comes from making **every node type, edge condition, and config field a typed, single-source case** on both sides — so adding/handling a case is one edit and a *missed* case fails loudly:

1. **Discriminated unions on `type`** — BE: `node.data` is a Pydantic `Annotated[Union[ConversationData, ToolData, TransferCallData, EndCallData, DecisionData], Field(discriminator="type_tag")]`; edge `condition` is `Union[AiCondition, LogicCondition]`. FE: a TS discriminated union `NodeData = ConversationData | ToolData | …`. Result: parsing rejects malformed per-type configs, and a `switch(node.type)` is **exhaustive** (TS `never` check / Python match) — you cannot forget a node type.
2. **One registry per side = single source of truth.** BE: a `NODE_HANDLERS: dict[WorkflowNodeType, NodeHandler]` and `CONDITION_EVALUATORS: dict[EdgeConditionType, fn]`. FE: `nodeRegistry.ts` drives palette + node component + config form + validation. Adding a node type = add a Pydantic model + a handler (BE) and a registry entry + component + form (FE). Nothing else changes.
3. **Presentation isolated from domain.** Only `position`/`viewport`/RF internals are visual; the runtime, validation, analytics, and Vapi export read **only** domain fields (`node.data`, `edge.data.condition`). On save the FE **strips RF runtime fields** (`selected`, `dragging`, `measured`, `width`, `height`) so stored JSON stays clean — i.e. there is always a tiny save-time sanitize regardless, so the canonical shape is chosen for domain cleanliness, not "zero transform" (which isn't achievable anyway).
4. **Forward-compatible + fault-tolerant.** `schemaVersion` lets `WorkflowGraph.parse()` migrate older graphs on read. Unknown node/condition types render as a generic "unsupported" node (with a validation warning) instead of crashing the editor or the call — important as the type set grows.
5. **Shared validation contract.** `validateGraph` (FE) and `WorkflowService.validate` (BE) implement the *same* rule set against the *same* typed model, so the editor's inline errors match what the API enforces on publish.

This is what makes "all cases" tractable: the structure is open for extension (new node/condition types) and closed for modification (existing handlers untouched), enforced by the type system rather than convention.

### Worked example graph (restaurant booking)

**(A) Vapi import/export form** — matches a Vapi export file (used only at Import/Export):

```jsonc
{
  "nodes": [
    { "name": "introduction", "type": "conversation", "isStart": true,
      "prompt": "You are Alex... identify intent: new / modify / cancel.",
      "messagePlan": { "firstMessage": "Hi! This is Alex from The Dine Spot. How may I help?" },
      "variableExtractionPlan": { "output": [ { "title": "user_intent", "type": "string", "enum": [], "description": "new/modify/cancel" } ] },
      "metadata": { "position": { "x": 700, "y": -40 } } },
    { "name": "get_name", "type": "conversation", "prompt": "Collect the customer's name.",
      "messagePlan": { "firstMessage": "Sure! May I have your name please?" },
      "variableExtractionPlan": { "output": [ { "title": "customer_name", "type": "string", "enum": [], "description": "" } ] },
      "metadata": { "position": { "x": -10, "y": 930 } } },
    { "name": "get_date", "type": "conversation", "prompt": "Collect reservation date as YYYY-MM-DD.",
      "messagePlan": { "firstMessage": "What date would you like to reserve?" },
      "variableExtractionPlan": { "output": [ { "title": "reservation_date", "type": "string", "enum": [], "description": "" } ] },
      "metadata": { "position": { "x": -600, "y": 1460 } } },
    { "name": "confirm_booking", "type": "conversation", "prompt": "Wait for a clear yes/no.",
      "messagePlan": { "firstMessage": "Confirm: a table for {{number_of_guests}} on {{reservation_date}} at {{reservation_time}} under {{customer_name}}. Correct?" },
      "metadata": { "position": { "x": -3, "y": 2633 } } },
    { "name": "book_table", "type": "tool", "toolId": "b98fb5c6-9852-4012-b54e-d134de927e62",
      "metadata": { "position": { "x": 264, "y": 3070 } } },
    { "name": "inform_manager", "type": "conversation", "prompt": "Give the manager's number for modify/cancel.",
      "messagePlan": { "firstMessage": "For changes, please call our manager at +91 97894 83349. Noted?" },
      "metadata": { "position": { "x": 1086, "y": 785 } } },
    { "name": "goodbye", "type": "endCall",
      "messagePlan": { "firstMessage": "Thanks for calling. Goodbye!" },
      "metadata": { "position": { "x": 482, "y": 3304 } } }
  ],
  "edges": [
    { "from": "introduction", "to": "get_name",      "condition": { "type": "ai", "prompt": "user_intent contains \"new\" or booking a table" } },
    { "from": "introduction", "to": "inform_manager", "condition": { "type": "ai", "prompt": "user_intent contains \"cancel\" or \"modify\"" } },
    { "from": "get_name",     "to": "get_date",       "condition": { "type": "ai", "prompt": "" } },
    { "from": "confirm_booking", "to": "book_table",  "condition": { "type": "ai", "prompt": "user said yes" } },
    { "from": "confirm_booking", "to": "get_date",    "condition": { "type": "ai", "prompt": "user said no" } },
    { "from": "book_table",   "to": "goodbye",        "condition": { "type": "logic", "prompt": "{{ booking_status == \"success\" }}" } },
    { "from": "inform_manager", "to": "goodbye",      "condition": { "type": "ai", "prompt": "user said yes" } }
  ],
  "globalPrompt": "Be calm, warm, and concise. Always read details back to confirm.",
  "artifactPlan": null   // optional, phase 2 (inline, no table)
}
```

**(B) Stored canonical form (React-Flow-native)** — this is what we persist in `workflow_versions.graph` and hand to `<ReactFlow>` **with no transform**. Same workflow as (A), each node's Vapi fields nested under `data`:

```jsonc
{
  "nodes": [
    { "id": "introduction", "type": "conversation", "position": { "x": 700, "y": -40 },
      "data": { "name": "introduction", "isStart": true,
        "prompt": "You are Alex... identify intent.",
        "messagePlan": { "firstMessage": "Hi! This is Alex from The Dine Spot. How may I help?" },
        "variableExtractionPlan": { "output": [ { "title": "user_intent", "type": "string", "enum": [], "description": "new/modify/cancel" } ] } } },
    { "id": "get_name", "type": "conversation", "position": { "x": -10, "y": 930 },
      "data": { "name": "get_name", "prompt": "Collect the customer's name.",
        "messagePlan": { "firstMessage": "Sure! May I have your name please?" },
        "variableExtractionPlan": { "output": [ { "title": "customer_name", "type": "string", "enum": [], "description": "" } ] } } },
    { "id": "confirm_booking", "type": "conversation", "position": { "x": -3, "y": 2633 },
      "data": { "name": "confirm_booking", "prompt": "Wait for a clear yes/no.",
        "messagePlan": { "firstMessage": "Confirm: a table for {{number_of_guests}} on {{reservation_date}} at {{reservation_time}} under {{customer_name}}. Correct?" } } },
    { "id": "book_table", "type": "tool", "position": { "x": 264, "y": 3070 },
      "data": { "name": "book_table", "toolId": "b98fb5c6-9852-4012-b54e-d134de927e62" } },
    { "id": "goodbye", "type": "endCall", "position": { "x": 482, "y": 3304 },
      "data": { "name": "goodbye", "messagePlan": { "firstMessage": "Thanks for calling. Goodbye!" } } }
  ],
  "edges": [
    { "id": "introduction->get_name", "source": "introduction", "target": "get_name", "type": "condition",
      "data": { "condition": { "type": "ai", "prompt": "user_intent contains \"new\" or booking a table" } } },
    { "id": "confirm_booking->book_table", "source": "confirm_booking", "target": "book_table", "type": "condition",
      "data": { "condition": { "type": "ai", "prompt": "user said yes" } } },
    { "id": "book_table->goodbye", "source": "book_table", "target": "goodbye", "type": "condition",
      "data": { "condition": { "type": "logic", "prompt": "{{ booking_status == \"success\" }}" } } }
  ],
  "globalPrompt": "Be calm, warm, and concise. Always read details back to confirm.",
  "artifactPlan": null   // optional, phase 2 (inline, no table)
}
```
The custom node component reads `props.data` (`data.prompt`, `data.messagePlan`, …); the custom edge reads `props.data.condition`. `<ReactFlow nodes={graph.nodes} edges={graph.edges} ...>` renders (B) directly.

### Alembic migration (new revision in `alembic/versions/`, `down_revision` = current head)

1. `op.create_table("workflows", ...)` (org-level container; columns per Table 1).
2. `op.create_table("workflow_versions", ...)` (`graph` server_default `'{"nodes":[],"edges":[],"globalPrompt":""}'::jsonb`; columns per Table 2).
3. Add the two cross-FKs `workflows.published_version_id` / `draft_version_id` → `workflow_versions.id` via `op.create_foreign_key(..., ondelete="SET NULL", use_alter=True)` (circular dependency between the two tables).
4. Indexes/constraints: `Index(ix_workflows_organization_id)`; `UniqueConstraint(organization_id, name)` on workflows; `Index(ix_workflow_versions_workflow_id)`; GIN on `workflow_versions.graph`; `UniqueConstraint(workflow_id, version)`.
5. `op.add_column("agent_configs", sa.Column("mode", sa.String(16), nullable=False, server_default="prompt"))`.
6. `op.add_column("agent_configs", sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=True))` + `op.create_foreign_key("fk_agent_configs_workflow", "agent_configs", "workflows", ["workflow_id"], ["id"], ondelete="SET NULL")`.
7. `downgrade()` drops the `agent_configs` FK + two columns, then the cross-FKs, then both workflow tables (children first).

> Note: purely **additive** with safe defaults — existing agents keep running in `'prompt'` mode untouched.

## BACKEND

### 1. Migration & models
- Implement the additive migration above.
- New `core/models/workflow.py` — `class Workflow(OrgScopedModel)` (Table 1) **and** `class WorkflowVersion(OrgScopedModel)` (Table 2), with relationships (`Workflow.versions`, plus `published_version`/`draft_version` via explicit `foreign_keys=`). Register both in `core/models/__init__.py`. (No extraction-schema model — extraction is per-node in the graph.)
- Edit `core/models/agent_config.py` — add `mode` + `workflow_id` columns (+ a `workflow` relationship).
- New `WorkflowNodeType(str, Enum)` in `core/models/enums.py` (**Vapi set + decision**): `conversation, tool, transfer_call, end_call, decision` (the **global** variant is `conversation` with `is_global=true`, not a separate type). New `EdgeConditionType(str, Enum)`: `ai, logic`.

### 2. Schemas (Pydantic) — canonical React-Flow-native graph (Vapi fields in `data`)
- Typed graph models in new `core/services/workflow/schema.py`, matching the persisted JSON:
  - `WorkflowGraph{ schemaVersion: int = 1, nodes: list[WorkflowNode], edges: list[WorkflowEdge], globalPrompt: str = "", artifactPlan: dict|None = None }` (`artifactPlan` optional, phase-2 inline — not modeled in v1).
  - `WorkflowNode{ id: str, type: WorkflowNodeType, position: XY, data: NodeData }` — top-level is React-Flow-native.
  - `NodeData` is a **discriminated union** on `type`: `ConversationData{name,isStart,isGlobal,condition?,prompt,messagePlan?,variableExtractionPlan?,toolIds[]}` · `ToolData{name,toolId?|tool?}` · `TransferCallData{name,destination,transferPlan?,messagePlan?}` · `EndCallData{name,messagePlan?}` · `DecisionData{name,prompt?}`. Each is its own Pydantic model (`Annotated[Union[...], Field(discriminator=...)]`) so per-type configs validate exhaustively. **No per-node `model`** — the LLM (provider/model/temperature/max_tokens) comes from the assigned agent's `AgentConfig.llm_settings` and applies to every node (keeps a workflow reusable across agents with different LLMs).
  - `MessagePlan{ firstMessage: str }`; `VariableExtractionPlan{ output: list[ExtractVar] }`; `ExtractVar{ title, type, enum: list=[], description: str }`; `InlineTool{ type: str }` (e.g. `endCall`); `XY{ x: float, y: float }`.
  - `WorkflowEdge{ id: str, source: str, target: str, type: str = "condition", data: EdgeData }`; `EdgeData{ condition: EdgeCondition }`; `EdgeCondition{ type: EdgeConditionType, prompt: str = "" }`.
  - The **Vapi import/export converter** (`core/services/workflow/vapi_adapter.py`) maps this ↔ Vapi's flat shape (`name`, `metadata.position`, `from`/`to`, `condition`); used only by import/export endpoints.
- Request/response in `core/api/v1/workflows.py`: `CreateWorkflowRequest{name,description}` (org-level — **no agent_id**), `SaveDraftRequest{workflow_id, graph: WorkflowGraph, expected_checksum}`, `WorkflowSummary{id,name,status,is_valid,updated_at,agents_using}`, `WorkflowDetail` (+ draft graph + version pointers), `ValidateWorkflowResponse`. The **assign** request lives on the agent side: fold into the existing agent `UpdateAgentRequest.config` as `mode` + `workflow_id`.

### 3. Services — two services, separating workflow CRUD from assignment

**`core/services/workflow/service.py` — `WorkflowService(BaseService)`** (org-level CRUD; auto org-scoping via `self.query`):
- `list() -> [WorkflowSummary]` — all org workflows (excl. soft-deleted), with a usage count of how many agent configs reference each.
- `create(name, description, user_id)` — insert container + initial draft version (Start-only graph); set `draft_version_id`. **No agent involved.**
- `get(workflow_id)` / `get_draft(workflow_id)` — container + editable draft graph.
- `save_draft(workflow_id, graph, expected_checksum, user_id)` — write into the draft version row; compute `graph_checksum`; `expected_checksum` mismatch → **409** (concurrent-edit guard); run `validate()` → store `is_valid`/`validation_errors`. Published version untouched ⇒ assigned agents' live calls unaffected.
- `validate(graph) -> [{code,node_name,message}]` — pure; checks below.
- `publish(workflow_id, user_id)` — require draft `is_valid`; clone draft → new `is_draft=false` snapshot (`version=++latest_version`), set `published_version_id`, `published_at`, `status='published'`; start a fresh draft. Invalidate the pipeline cache for **every agent config whose `workflow_id` == this workflow** so the new graph goes live.
- `list_versions(workflow_id)` / `delete(workflow_id)` — soft-delete; refuse (or warn) if any `agent_configs.workflow_id` still references it; `SET NULL` FK is the backstop.

**Assignment (agent side)** — extend `core/services/agent_service.py` `AgentService` (where config writes already happen): when an update sets `config.mode`/`config.workflow_id`, validate the referenced workflow is org-owned and has a `published_version_id` (else 400), persist onto the live `AgentConfig`, and invalidate that agent's pipeline cache. This keeps "which workflow is assigned" inside the agent-config write path.

- `validate` checks (canonical graph): node `id`s unique; exactly one node with `data.isStart=true`; every edge `source`/`target` references an existing node `id`; no orphan/unreachable nodes (BFS from start; global nodes exempt); ≥1 reachable terminal (`endCall` or `transferCall`); terminal nodes have 0 outgoing; `logic` edge condition parses as a Liquid boolean; `tool` nodes' `data.toolId` exists + org-scoped (or `data.tool.type` is a known built-in). At **assign** time also reject if the agent's `is_s2s` is true.

### 4. API routers
**Workflow CRUD — new `core/api/v1/workflows.py`** (follow `agents.py` patterns; register in `main.py` + `main_ee.py` as `prefix="/workflow"`):
`GET /workflow/list` (all org workflows) · `POST /workflow/create` · `GET /workflow/get?workflow_id=` (container + draft graph) · `POST /workflow/save_draft` · `POST /workflow/validate` · `POST /workflow/publish` · `GET /workflow/list_versions?workflow_id=` · `DELETE /workflow/delete?workflow_id=` · `POST /workflow/import_vapi` (Vapi JSON → canonical) · `GET /workflow/export_vapi?workflow_id=` (canonical → Vapi JSON). (No extraction-schema endpoints — extraction is per-node in the graph.)

**Assignment — on the agent router** (`core/api/v1/agents.py`): either reuse `PUT /agent/update_agent` (add `mode` + `workflow_id` to `AgentConfigRequest`) or add a focused `POST /agent/assign_workflow {agent_id, workflow_id}` / `POST /agent/set_workflow_mode {agent_id, mode}`. Recommended: extend `AgentConfigRequest` so assignment flows through the existing save/version machinery for free.

### 5. Runtime engine — new subpackage `core/services/pipeline/workflow/`
```
graph.py        WorkflowGraph dataclass: nodes keyed by id (== data.name), reads Vapi fields from node.data,
                outgoing-edge lookup (edge.source/target), reachability
context.py      WorkflowCallContext{variables, current_node_id, history[], visit_counts}
engine.py       WorkflowEngine: start() -> NodeDirective; on_user_turn(text) -> NodeDirective
conditions.py   evaluate an edge condition: type=="logic" → render LiquidJS prompt over variables
                → truthy? (deterministic, no LLM); type=="ai" → LLM yes/no on plain-language prompt.
                Empty prompt = always-true. Global-node enter conditions evaluated here too.
extractor.py    per-node variableExtractionPlan.output[] → one extraction LLM call after the
                node fills those variables into context (Vapi's approach); merges into context.variables
navigator.py    pick the next node: eval outgoing edges in order (logic first, then ai); first satisfied
                wins. For a "decision" node this runs immediately on entry (no turn).
handlers/       base.py (NodeHandler ABC) + conversation, tool, transfer_call, end_call, decision;
                registry NODE_HANDLERS[WorkflowNodeType]→handler + CONDITION_EVALUATORS[EdgeConditionType]→fn
                (add a node/condition type = add a model + register one handler — exhaustive, nothing else changes)
```
`NodeDirective{system_prompt, speak?, end_call?, transfer_to?, register_tools[], stay?}`.
- **Edge routing follows Vapi**: `logic` conditions evaluated in Python via a Liquid renderer over `context.variables` (+ built-ins); `ai` conditions via a cheap LLM yes/no. No "pick-edge-by-id" mega-call — each edge is judged by its own condition, matching the saved `condition:{type,prompt}`.
- **Decision node**: on entry, no speech/turn — immediately evaluate outgoing edges and jump (pure router).
- **Global nodes** (`isGlobal:true` + `condition`): after every turn, their enter conditions are checked first; if satisfied, jump there regardless of current node (Vapi semantics).

Integration points (extend, don't rewrite):
- `core/services/pipeline/service_resolver.py` `load_agent_service_config()`: when `config.mode == "workflow"` and `config.workflow_id` is set, load that `Workflow` → its `published_version_id` → that version's `graph`; embed as `result["workflow"]`. If mode is `workflow` but `workflow_id` is null / has no published version, fall back to prompt mode (and log). Add `config.workflow_id` + the published version's `updated_at` to `compute_agent_cache_version` and bump `PAYLOAD_FORMAT_VERSION` (so re-assign / re-publish invalidates live calls).
- `core/services/pipeline/params/base.py`: add `workflow: Optional[dict]` field + `is_workflow` property; populate in `from_cache_dict`.
- `core/services/pipeline/workflow/__init__.py`: register a `"pipecat-workflow"` engine `{PipecatPipelineParams, PipecatPipelineBuilder, WorkflowPipelineRunner}`.
- `core/bot.py` `run_bot()`: select engine via `params.is_workflow` (one-line branch).
- `WorkflowPipelineRunner(PipecatPipelineRunner)` — reuse ALL call-log/recording/transcript/metrics machinery; override only: (a) seed initial LLM context + first message from the `isStart` node, (b) the `on_user_turn_stopped` handler → `await engine.on_user_turn(text)` then apply `NodeDirective` (mutate the Pipecat `LLMContext` system message, queue `TTSSpeakFrame` for `speak`, register/unregister node-scoped tools on the LLM service, transfer/end as directed).
- **Prompt layering**: the conversation node handler builds `NodeDirective.system_prompt` by composing `AgentConfig.system_prompt_template` (persona, carried in params) + `graph.globalPrompt` + `node.prompt`, then renders `{{variables}}` via `prompt_variables.substitute_variables` (Liquid). Persona + global are constant across turns (cache-friendly); only the node layer changes per node. The node's `messagePlan.firstMessage` is spoken on entry (also variable-substituted).
- **Reuse existing infra**: `prompt_variables.substitute_variables`/`build_call_context` for `{{var}}` + built-ins; **`tool` nodes resolve via the existing `Tool` model** — `custom_tool_service` handlers for webhook/custom tools, the MCP tool-schema builders for MCP tools, and inline `tool.type` built-ins (`endCall`, `transferCall`, `sms`) via existing paths; existing transfer + `end_call_message` + `CallEndDetectorProcessor` for `transferCall`/`endCall` nodes.
- **Traversal analytics**: write `context.history` (node id/type/entered/exited/reason/vars) + final `variables` into the Call record (`pipeline_config["workflow"]` or `metadata_["workflow"]`) in the existing `complete_call` path — no new table in v1.

### Backend edge cases
Infinite re-prompt → `ConversationData.max_visits` + `visit_counts` short-circuit. Dead-ends blocked at validation; runtime fallback → graceful end. Concurrent edits → checksum 409. Large graphs → cap nodes (~300) at validation. Navigator latency → fuse extraction+routing into one call; skip LLM when deterministic. Backward compat → `mode` defaults `'prompt'`; new code paths only run when `mode=='workflow'`.

---

## FRONTEND

Install **`@xyflow/react`** (v12) — `cd frontend && yarn add @xyflow/react`. (`framer-motion` already present; `@tanstack/react-query` unused — use Jotai per codebase convention. MUI-free.)

### 1a. Standalone Workflows feature (top-level — where create/list/edit live)

A new top-level dashboard area, parallel to Agents/Tools/Knowledge Base — **not** inside the agent editor.

- **Sidebar nav**: add a `Workflows` entry to `NAV_SECTIONS` in `frontend/src/components/layout/sidebar.tsx` (Build group, e.g. `GitBranch`/`Workflow` icon).
- **Routes** (App Router, under `(dashboard)`):
  - `frontend/src/app/(dashboard)/workflows/page.tsx` → thin wrapper → `WorkflowListPage` (list of all org workflows: name, status, validity, # agents using it; New / Edit / Duplicate / Delete; mirrors `AgentListPage` with `CustomTable` + faceted list).
  - `frontend/src/app/(dashboard)/workflows/[id]/page.tsx` → thin wrapper → `WorkflowBuilder` (the **full-page** React Flow canvas editor for one workflow). This is a "focused" full-screen route (the dashboard layout already hides the sidebar for agent create/edit; add `workflows/[id]` to that focused-route predicate so the canvas gets the full width).
- **Create**: `CreateWorkflowModal` (name + description) → `POST /workflow/create` → navigate to `/workflows/[id]`.
- The editor edits the **draft** only; toolbar has **Save draft** (checksum-guarded autosave), **Publish**, validation popover, back-to-list, a **"Global prompt"** settings button (drawer with a `RichPromptEditorField` writing `graph.globalPrompt`). The published graph (and any assigned agents' live calls) are untouched until Publish. (Call-wide extraction-schema manager is **phase 2**, inline in `graph.artifactPlan` — no table.)
- **No load/save transform**: the stored graph is already React-Flow-native (`{id,type,position,data}` nodes, `{id,source,target,data}` edges), so `<ReactFlow nodes={graph.nodes} edges={graph.edges}>` renders it directly and saving writes it back as-is. The **Vapi import/export converter** (`workflowGraphUtils.ts` `fromVapi`/`toVapi`) is used only for "Import Vapi JSON" / "Export Vapi JSON": `name↔id`, `metadata.position↔position`, flatten/nest `data`, `from/to↔source/target`, `condition↔data.condition`.

### 1b. Assignment control inside the agent editor (the ONLY workflow touchpoint in the agent)

- `frontend/src/components/agents/agent-form/sectionNav.ts`: no canvas section. Instead surface assignment inside an existing config section (recommend the **AI** step, or a small new **"Workflow"** section that renders just the assignment control — *not* a canvas).
- The control: a **flow-driver toggle** (Single prompt vs Workflow) + a `SearchableSelect` of the org's **published** workflows (fetched via the workflows list atom), plus a "Edit workflow ↗" link that deep-links to `/workflows/[id]`. Writing it sets `config.mode` + `config.workflow_id` through the **existing agent save/version flow** (`AgentFormState` → `formStateToUpdatePayload`), so assignment versions with the rest of the config.
- **The Prompt section is NOT hidden in Workflow mode** — research shows persona + workflow are layered. Show a hint on the Prompt step: "In Workflow mode this is the global persona, layered above the workflow's global prompt and each node's prompt." So both are used together; the toggle only decides whether the graph controls turn-to-turn flow (UI warns if Workflow mode is on but no workflow is selected).

### 2. React Flow canvas
- `next/dynamic` import with `ssr:false` (React Flow measures the DOM); wrap in `<ReactFlowProvider>`; `import '@xyflow/react/dist/style.css'`.
- Controlled state via `useNodesState`/`useEdgesState` (local — NOT Jotai source of truth); mirror only coarse facts (node count, validation issues, dirty, selectedNodeId) into a Jotai status atom.
- `<Background dots>`, `<Controls>`, `<MiniMap>`, `fitView`, `defaultEdgeOptions{type:'condition', markerEnd: ArrowClosed}`, `onConnect`/`onNodesChange`/`onEdgesChange`, drag-drop from palette (`onDragOver`/`onDrop` + `screenToFlowPosition`).
- `colorMode={resolvedTheme}` (next-themes) for dark mode; override `--xy-*` CSS vars to match theme tokens.

### 3. File tree (new) — standalone feature under `frontend/src/components/workflows/`
```
WorkflowListPage.tsx             top-level list of ALL org workflows (CustomTable + faceted list):
                                 status, validity, #agents using; New/Edit/Duplicate/Delete
CreateWorkflowModal.tsx          CustomModal: name + description → POST /workflow/create
WorkflowBuilder.tsx              full-page editor entry: provider + layout (canvas|palette|drawer), draft load/save
WorkflowToolbar.tsx              in-canvas bar: name, draft/published status, Save draft, Publish, validation, back
WorkflowEmptyState.tsx           zero-node hint (single Start node)
nodeRegistry.ts                  NodeTypeMeta registry: type→{label,icon,accent,category,
                                 defaultData,sourceHandles,hasTarget,terminal,deletable}
                                 — single source for palette, createNode, nodeTypes, validation
canvas/
  WorkflowCanvas.tsx             <ReactFlow> wiring
  nodeTypes.ts                   memoized nodeTypes map
  nodes/BaseNode.tsx             shared card: icon chip + type + title + summary + handles +
                                 selected ring + error badge (CustomTooltip) + isStart/global chip
  nodes/{Conversation,Tool,TransferCall,EndCall,Decision}Node.tsx   (Vapi node set + decision)
  edges/ConditionEdge.tsx        labeled edge showing condition.type (AI/Logic) + prompt; "+" add-node (phase 1.1)
palette/
  NodePalette.tsx                searchable, categorized "Add New Node" (Conversation/Decision/Tool/Transfer/End)
  PaletteItem.tsx                draggable row (also click-to-add for a11y)
config/
  NodeConfigDrawer.tsx           CustomDrawer; resolves per-type form by node.type
  forms/ConversationNodeForm.tsx prompt (RichPromptEditorField) + messagePlan.firstMessage +
                                 variableExtractionPlan editor + toolIds + isStart toggle +
                                 isGlobal toggle (+ enter condition when global). No model picker — the agent's LLM is used.
  forms/ToolNodeForm.tsx         pick existing Tool (SearchableSelect over getAllTools, covers webhook/custom/MCP)
                                 OR inline built-in tool.type (endCall/transferCall/sms)
  forms/TransferCallNodeForm.tsx destination + transferPlan + firstMessage
  forms/EndCallNodeForm.tsx      messagePlan.firstMessage
  forms/DecisionNodeForm.tsx     optional routing guidance prompt (branches live on its edges)
  EdgeConditionEditor.tsx        edits an edge's condition: type toggle AI | Logic + prompt
                                 (AI = plain language; Logic = Liquid {{ }} expression w/ var hints)
  VariableExtractionEditor.tsx   add/remove rows → variableExtractionPlan.output[{title,type,enum,description}]
useWorkflowHistory.ts            undo/redo snapshot stack (phase 1.1)
```
Assignment control under the agent editor:
```
frontend/src/components/agents/agent-form/steps/WorkflowAssignStep.tsx
                                 mode toggle + SearchableSelect of published workflows +
                                 "Edit workflow ↗" deep-link; writes config.mode + config.workflow_id
```
Page wrappers + nav:
```
frontend/src/app/(dashboard)/workflows/page.tsx        → WorkflowListPage
frontend/src/app/(dashboard)/workflows/[id]/page.tsx   → WorkflowBuilder (full-screen)
edit frontend/src/components/layout/sidebar.tsx        add "Workflows" nav entry
edit (dashboard)/layout.tsx focused-route predicate     add /workflows/[id] (hide sidebar)
```
New shared-layer files:
```
frontend/src/types/workflow.ts            canonical RF-native types: RFNode<NodeData>, NodeData = DISCRIMINATED UNION on type
                                          (ConversationData | ToolData | TransferCallData | EndCallData | DecisionData) →
                                          exhaustive switch (TS `never` check); RFEdge<{condition:{type:'ai'|'logic',prompt}}>;
                                          graph{schemaVersion,nodes,edges,globalPrompt,artifactPlan}; WorkflowSummary/Detail
frontend/src/services/workflowService.ts  axios CRUD vs /workflow/* (list/create/get/save_draft/validate/publish/list_versions/delete/import_vapi/export_vapi)
frontend/src/atoms/WorkflowAtom.tsx       list atom (org workflows) + editor status atom + write atoms:
                                          fetchWorkflowList/createWorkflow/fetchDraft/saveDraft/validate/
                                          publish/deleteWorkflow (mirror AgentsAtom).
                                          (Assignment is written via the existing AgentsAtom update path.)
frontend/src/utils/workflowGraphUtils.ts  defaultGraph (one isStart conversation node), createNode, validateGraph;
                                          Vapi import/export converter fromVapi/toVapi (NOT used on normal load/save)
```

### 4. Node config + palette + UX
- **Config drawer** = `CustomDrawer` (~420px), one per-type RHF sub-form seeded from the node, debounced writeback via `updateNode(id, patch)`. All inputs use **shared components** (`TextInput`, `TextAreaField`, `SelectInput`, `SearchableSelect`, `CheckboxField`, `SliderField`, `RichPromptEditorField`) with the `control` prop. Tool form reuses `getAllTools()` (covers webhook/custom/MCP). No model picker (the assigned agent's LLM drives all nodes). `isStart`/`isGlobal` toggles + delete in the drawer header.
- **Edge editing**: clicking an edge opens `EdgeConditionEditor` — a **type toggle (AI ↔ Logic)** + a prompt field (AI = plain language; Logic = Liquid `{{ }}` with available-variable hints), matching the saved `condition:{type,prompt}`.
- **Palette** driven by `nodeRegistry.ts`: Conversation, Decision, Tool, Transfer Call, End Call (+ "make global" via the conversation node's toggle).
- **UX**: theme-token-driven node accents (reuse `bg-{c}/10 ring-1 ring-inset text-{c}` from `ToolsMcpStep`), framer-motion panel/drawer transitions, empty state = single `isStart` conversation node, client-side `validateGraph` (debounced) → node error badges + toolbar issue popover (click → `fitView` to node), Sonner toasts + `handleApiError`, Radix focus handling, dark mode.

### 5. Client-side data layer
- `WorkflowAtom.tsx` write atoms call `workflowService.ts` (components never import services directly — DIP rule). The list atom is org-scoped (all workflows); draft save is **dedicated** (graph is large) and keyed by `workflow_id`, checksum-guarded. The canvas works in the canonical RF-native shape directly (no load/save transform); the Vapi converter is used only for import/export. `validateGraph` mirrors backend checks (one `isStart`, dangling edge, orphan/unreachable, terminal-with-outgoing, required-field gaps). **Assignment** flows through the existing agent update atoms (`config.mode` + `config.workflow_id`); `WorkflowAssignStep` reads the workflows list atom for its published-workflow dropdown.

---

## Phasing
- **v1 (this build)**: standalone **Workflows** page (list, create, **draft edit + autosave, publish**) + per-agent **assignment** in the agent config + DB (React-Flow-native graph with Vapi fields in `data`, Vapi import/export) + API + runtime. **Node types**: `conversation` (prompt + `messagePlan.firstMessage` + `variableExtractionPlan`; LLM from the agent config), `decision`, `tool` (toolId → webhook/custom/MCP/built-in, incl. inline `endCall`), `transferCall`, `endCall`, and **global** conversation nodes. **Edges**: `ai` + `logic` conditions. Layered prompts (persona + `globalPrompt` + node prompt). Traversal recorded on Call; client+server validation.
- **Phase 2**: call-wide extraction schemas stored inline in `graph.artifactPlan` (no table) + call-end extraction; add-node-on-edge "+", undo/redo, auto-layout ("Tidy" via elkjs/dagre); Test/Simulate panel; version diff/rollback; sub-workflow / transfer-to-pathway; DTMF/SMS dedicated nodes; S2S workflow support.

---

## Verification
**Backend**
1. `alembic upgrade head` → confirm `workflows` + `workflow_versions` tables and `agent_configs.mode` + `agent_configs.workflow_id` (FK) exist; existing agents still load (mode defaults `'prompt'`).
2. Run `python main.py`; exercise the lifecycle via Postman/curl using the **canonical graph** (example B): `/workflow/create` → `/save_draft` → `/validate` (assert "no isStart" / dangling-edge / orphan errors fire) → `/publish`. Also test `/workflow/import_vapi` with a Vapi file → it converts to canonical; `/workflow/export_vapi` → returns Vapi shape. Then on the agent side, assign it (`PUT /agent/update_agent` with `config.mode='workflow'` + `config.workflow_id`) and confirm a second agent can be assigned the **same** workflow (reuse). Confirm assigning a draft-only workflow is rejected; deleting a workflow `SET NULL`s the referencing config (agent falls back to prompt mode).
3. Unit-test `WorkflowService.validate()` against malformed graphs; test `logic` condition evaluation (Liquid `{{ x == true }}`) and `ai` condition routing; test the decision node routes on entry; test publish snapshots the draft + leaves the live published version intact for assigned agents until re-publish.
4. Place a test call (Daily/Twilio) against an agent in workflow mode with an assigned workflow; verify: `isStart` node `firstMessage`, per-node `variableExtractionPlan` filling `{{variables}}` used in a later `firstMessage`, an `ai` edge transition by intent, a `logic` edge transition by variable, a `tool` node firing mid-call, a global node interrupt, and `endCall`/`transferCall` terminating. Confirm `context.history` lands on the Call record. Edit + publish mid-test → next call uses the new graph; in-flight call unaffected.
5. Regression: a `mode='prompt'` agent runs byte-identically (no new code paths touched).

**Frontend**
1. `cd frontend && yarn add @xyflow/react && yarn dev`.
2. **Workflows** page (top-level nav): create two workflows; open one → canvas editor (drag Conversation/Decision/Tool/Transfer/End nodes, connect edges, set each edge's condition AI↔Logic, configure per-node prompt/firstMessage/variable-extraction in the drawer, set `globalPrompt`), Save draft, reload → draft round-trips (canonical RF-native graph renders with no transform). Test **Import Vapi JSON** → converts to canonical and renders; **Export** → back to Vapi shape. Publish a valid one.
3. Open an agent → assignment control: switch mode to Workflow, pick a published workflow from the dropdown, save → confirm the config persists `mode`+`workflow_id`. Assign the **same** workflow to a second agent (reuse works). "Edit workflow ↗" deep-links to `/workflows/[id]`.
4. Trigger validation errors (delete start / orphan a node) → node badges + toolbar issues appear; publish is blocked until valid.
5. `yarn lint` + `yarn build` clean.

## Risk callout
The **runtime engine** (`core/services/pipeline/workflow/`) is the highest-risk piece — it mutates the live Pipecat `LLMContext` between turns and adds a navigator LLM call. Build it behind the `mode=='workflow'` branch so prompt-mode agents are never affected, and validate with real test calls before any rollout.
