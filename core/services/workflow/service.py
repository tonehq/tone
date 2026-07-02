"""WorkflowService — agent-scoped CRUD + draft/publish/validate for visual workflows."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from core.models.agent import Agent
from core.models.agent_config import AgentConfig
from core.models.workflow import Workflow, WorkflowVersion
from core.services.base import BaseService
from core.services.workflow import schema as wf_schema
from core.services.workflow import vapi_adapter

# Every workflow has a single working row at version 0 (there are no published
# snapshots anymore — the agent version's own publish is the "go live" gate).
_DRAFT_VERSION = 0


def _checksum(graph: Dict[str, Any]) -> str:
    canonical = json.dumps(graph, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _api_request_secret_rows(graph: Dict[str, Any]):
    """Yield (node_id, row) for every apiRequest header/staticBody row marked encrypt."""
    for n in (graph or {}).get("nodes") or []:
        if not isinstance(n, dict) or n.get("type") != "apiRequest":
            continue
        nid = n.get("id")
        data = n.get("data") or {}
        for field in ("headers", "staticBody"):
            for row in data.get(field) or []:
                if isinstance(row, dict) and row.get("encrypt"):
                    yield nid, field, row


def _secret_lookup_keys(nid, field: str, row: Dict[str, Any]) -> List[tuple]:
    """Identity keys used to match a masked (blanked) row back to its stored secret.
    Prefer the stable row id ``_rid`` — it survives a header/field-key rename — and fall
    back to the (mutable) key for rows saved before row ids existed."""
    keys: List[tuple] = []
    rid = row.get("_rid")
    if isinstance(rid, str) and rid.strip():
        keys.append((nid, field, "rid", rid.strip()))
    name = (row.get("key") or "").strip()
    if name:
        keys.append((nid, field, "key", name))
    return keys


def _encrypt_graph_secrets(graph: Dict[str, Any], prev_graph: Optional[Dict[str, Any]] = None) -> None:
    """Encrypt encrypt-flagged header/static values in place (AES, idempotent via the
    ``_encrypted`` marker). An empty value carries over the previously-saved secret from
    ``prev_graph`` so masking-then-saving (the UI never receives plaintext) doesn't wipe it.
    Carry-over matches on the stable row id first (so renaming a key preserves the secret),
    then on the key name for older rows that predate row ids."""
    from core.utils.encryption import encrypt

    prev: Dict[tuple, str] = {}
    if prev_graph:
        for nid, field, row in _api_request_secret_rows(prev_graph):
            if row.get("_encrypted") and row.get("value"):
                for k in _secret_lookup_keys(nid, field, row):
                    prev.setdefault(k, row["value"])

    for nid, field, row in _api_request_secret_rows(graph):
        val = row.get("value") or ""
        if row.get("_encrypted") and val:
            continue
        if not val:
            carried = next(
                (prev[k] for k in _secret_lookup_keys(nid, field, row) if k in prev), None
            )
            if carried:
                row["value"] = carried
                row["_encrypted"] = True
            continue
        row["value"] = encrypt(val)
        row["_encrypted"] = True


def _mask_graph_secrets(graph: Dict[str, Any]) -> Dict[str, Any]:
    """Return a deep copy with encrypted secret values blanked so the editor never receives
    ciphertext or plaintext — the row keeps ``encrypt``/``_encrypted`` so the UI shows a
    'saved' placeholder and an empty submit carries the secret over."""
    import copy

    g = copy.deepcopy(graph or {})
    for _nid, _field, row in _api_request_secret_rows(g):
        if row.get("_encrypted"):
            row["value"] = ""
    return g


class WorkflowService(BaseService):
    # ── lookups ────────────────────────────────────────────────────────────
    def _get(self, workflow_id: str) -> Workflow:
        try:
            wid = UUID(str(workflow_id))
        except (ValueError, TypeError):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
        wf = (
            self.query(Workflow)
            .filter(Workflow.id == wid, Workflow.deleted_at.is_(None))
            .first()
        )
        if not wf:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
        return wf

    def _version(self, version_id) -> Optional[WorkflowVersion]:
        if not version_id:
            return None
        return (
            self.query(WorkflowVersion)
            .filter(WorkflowVersion.id == version_id, WorkflowVersion.deleted_at.is_(None))
            .first()
        )

    def _agents_using(self, workflow_id: UUID) -> int:
        # Count DISTINCT agents — agent_configs are versioned, so a single agent can have
        # several config rows referencing the same workflow; without distinct this over-counts
        # (and could wrongly block delete for a workflow only referenced by a stale version).
        return (
            self.query(AgentConfig)
            .with_entities(AgentConfig.agent_id)
            .filter(AgentConfig.workflow_id == workflow_id, AgentConfig.deleted_at.is_(None))
            .distinct()
            .count()
        )

    def _configs_using(self, workflow_id: UUID) -> int:
        # Count live config rows (agent versions) — a workflow referenced by ANY live
        # version must not be deleted, even if all references are from one agent.
        return (
            self.query(AgentConfig)
            .filter(AgentConfig.workflow_id == workflow_id, AgentConfig.deleted_at.is_(None))
            .count()
        )

    def _assigned_versions(self, workflow_id: UUID) -> List[int]:
        rows = (
            self.query(AgentConfig)
            .with_entities(AgentConfig.version)
            .filter(AgentConfig.workflow_id == workflow_id, AgentConfig.deleted_at.is_(None))
            .order_by(AgentConfig.version.asc())
            .all()
        )
        return [v for (v,) in rows]

    def _resolve_agent(self, agent_id) -> Agent:
        try:
            aid = UUID(str(agent_id))
        except (ValueError, TypeError):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
        agent = (
            self.query(Agent)
            .filter(Agent.id == aid, Agent.deleted_at.is_(None))
            .first()
        )
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
        return agent

    # ── list / get ─────────────────────────────────────────────────────────
    def list(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        q = self.query(Workflow).filter(Workflow.deleted_at.is_(None))
        if agent_id:
            agent = self._resolve_agent(agent_id)
            q = q.filter(Workflow.agent_id == agent.id)
        rows = q.order_by(Workflow.updated_at.desc()).all()
        return [self.summary(wf) for wf in rows]

    def summary(self, wf: Workflow) -> Dict[str, Any]:
        draft = self._version(wf.draft_version_id)
        return {
            "id": str(wf.id),
            "name": wf.name,
            "description": wf.description,
            "is_valid": bool(draft.is_valid) if draft else False,
            "agents_using": self._agents_using(wf.id),
            "agent_id": str(wf.agent_id) if wf.agent_id else None,
            "assigned_versions": self._assigned_versions(wf.id),
            "updated_at": wf.updated_at.isoformat() if wf.updated_at else None,
        }

    def detail(self, wf: Workflow) -> Dict[str, Any]:
        draft = self._version(wf.draft_version_id)
        return {
            "id": str(wf.id),
            "name": wf.name,
            "description": wf.description,
            "agents_using": self._agents_using(wf.id),
            "agent_id": str(wf.agent_id) if wf.agent_id else None,
            "assigned_versions": self._assigned_versions(wf.id),
            "draft_version_id": str(wf.draft_version_id) if wf.draft_version_id else None,
            "graph": _mask_graph_secrets(draft.graph if draft else wf_schema.empty_graph()),
            "graph_checksum": draft.graph_checksum if draft else None,
            "is_valid": bool(draft.is_valid) if draft else False,
            "validation_errors": (draft.validation_errors or []) if draft else [],
            "created_at": wf.created_at.isoformat() if wf.created_at else None,
            "updated_at": wf.updated_at.isoformat() if wf.updated_at else None,
        }

    def get(self, workflow_id: str) -> Dict[str, Any]:
        return self.detail(self._get(workflow_id))

    # ── create ─────────────────────────────────────────────────────────────
    def create(
        self,
        name: str,
        description: Optional[str],
        user_id: Optional[UUID],
        graph: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id is required")
        name = name.strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workflow name is required")

        agent = self._resolve_agent(agent_id) if agent_id else None

        # Friendly duplicate-name check scoped to the owning agent (legacy org-level
        # rows keep the org-wide check; the partial DB index is their backstop).
        dup_q = self.query(Workflow).filter(
            Workflow.name == name, Workflow.deleted_at.is_(None)
        )
        dup_q = dup_q.filter(Workflow.agent_id == (agent.id if agent else None))
        if dup_q.first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f'A workflow named "{name}" already exists. Choose a different name.',
            )

        graph = graph or wf_schema.empty_graph()
        size_err = wf_schema.graph_size_error(graph)
        if size_err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=size_err)
        _encrypt_graph_secrets(graph)
        errors = wf_schema.validate_graph(graph)

        wf = Workflow(
            organization_id=self.org_id,
            name=name,
            description=description,
            created_by_user_id=user_id,
            agent_id=agent.id if agent else None,
        )
        self.db.add(wf)

        draft = WorkflowVersion(
            organization_id=self.org_id,
            workflow_id=wf.id,
            version=_DRAFT_VERSION,
            graph=graph,
            start_node_name=wf_schema.find_start_node_name(graph),
            graph_checksum=_checksum(graph),
            is_valid=(len(errors) == 0),
            validation_errors=errors,
            created_by_user_id=user_id,
        )

        try:
            self.db.flush()  # assign wf.id
            draft.workflow_id = wf.id
            self.db.add(draft)
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f'A workflow named "{name}" already exists. Choose a different name.',
            )
        wf.draft_version_id = draft.id
        self.db.commit()
        return self.detail(wf)

    # ── clone ──────────────────────────────────────────────────────────────
    def clone(
        self,
        workflow_id: str,
        user_id: Optional[UUID],
        name: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Duplicate a workflow's graph into a NEW workflow. Uses the caller-provided
        ``name`` when given (surfacing ``create``'s 409 on a duplicate), otherwise
        auto-names it "<name> (clone)". The clone keeps the source's owning agent
        unless ``agent_id`` overrides it. Only the graph is copied — agent
        assignments are NOT carried over. Encrypted apiRequest secrets round-trip
        unchanged because ``create`` re-runs the idempotent secret encryption."""
        import copy

        src = self._get(workflow_id)
        draft = self._version(src.draft_version_id)
        graph = copy.deepcopy(draft.graph) if (draft and draft.graph) else wf_schema.empty_graph()

        owner_id = agent_id or (str(src.agent_id) if src.agent_id else None)
        new_name = (name or "").strip() or self._unique_clone_name(src.name, owner_id)
        return self.create(new_name, src.description, user_id, graph=graph, agent_id=owner_id)

    def _unique_clone_name(self, base: str, agent_id: Optional[str] = None) -> str:
        """"<base> (clone)", disambiguated with a numeric suffix if already taken within
        the same owner scope, so the clone never collides with ``create``'s guard."""
        base = (base or "Workflow")[:180]  # leave room for the " (clone) N" suffix (name ≤ 200)
        owner = UUID(str(agent_id)) if agent_id else None
        candidate = f"{base} (clone)"
        n = 2
        while (
            self.query(Workflow)
            .filter(
                Workflow.name == candidate,
                Workflow.deleted_at.is_(None),
                Workflow.agent_id == owner,
            )
            .first()
        ):
            candidate = f"{base} (clone) {n}"
            n += 1
        return candidate

    # ── per-agent-version deep copy ────────────────────────────────────────
    def duplicate_for_agent_version(
        self, source_workflow_id, agent_id: UUID, user_id: Optional[UUID]
    ) -> Workflow:
        """Deep-copy a workflow for a newly created agent version so each version owns
        an independent copy (editing one never affects another).

        Copies the single working graph. Flush-only: no commit and no name suffix, so
        the copy joins the caller's transaction (agent ``save_as_new_version``) and
        rolls back with it. Encrypted apiRequest secrets are carried verbatim inside
        the copied graph JSON (same org-level AES key)."""
        import copy

        src = self._get(source_workflow_id)
        draft = self._version(src.draft_version_id)

        wf = Workflow(
            organization_id=self.org_id,
            name=src.name,
            description=src.description,
            created_by_user_id=user_id or src.created_by_user_id,
            agent_id=agent_id,
        )
        self.db.add(wf)
        self.db.flush()

        if draft:
            draft_copy = WorkflowVersion(
                organization_id=self.org_id,
                workflow_id=wf.id,
                version=_DRAFT_VERSION,
                graph=copy.deepcopy(draft.graph),
                start_node_name=draft.start_node_name,
                graph_checksum=draft.graph_checksum,
                is_valid=draft.is_valid,
                validation_errors=copy.deepcopy(draft.validation_errors or []),
                created_by_user_id=user_id or draft.created_by_user_id,
            )
            self.db.add(draft_copy)
            self.db.flush()
            wf.draft_version_id = draft_copy.id

        self.db.flush()
        return wf

    # ── save draft ─────────────────────────────────────────────────────────
    def save_draft(
        self,
        workflow_id: str,
        graph: Dict[str, Any],
        expected_checksum: Optional[str],
        user_id: Optional[UUID],
    ) -> Dict[str, Any]:
        size_err = wf_schema.graph_size_error(graph)
        if size_err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=size_err)
        wf = self._get(workflow_id)
        draft = self._version(wf.draft_version_id)
        if not draft:
            # Recover: create the working version if somehow missing.
            draft = WorkflowVersion(
                organization_id=self.org_id,
                workflow_id=wf.id,
                version=_DRAFT_VERSION,
                graph=graph,
                created_by_user_id=user_id,
            )
            self.db.add(draft)
            self.db.flush()
            wf.draft_version_id = draft.id

        if expected_checksum and draft.graph_checksum and expected_checksum != draft.graph_checksum:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This workflow was changed elsewhere. Reload before saving.",
            )

        _encrypt_graph_secrets(graph, prev_graph=draft.graph)
        errors = wf_schema.validate_graph(graph)
        draft.graph = graph
        draft.start_node_name = wf_schema.find_start_node_name(graph)
        draft.graph_checksum = _checksum(graph)
        draft.is_valid = len(errors) == 0
        draft.validation_errors = errors
        self.db.commit()

        # Saving is the only "go live" step for a workflow now — drop the pipeline
        # cache so assigned agents pick up the edited graph on the next call.
        self._invalidate_assigned_agents(wf.id)
        return self.detail(wf)

    # ── validate (no persistence) ──────────────────────────────────────────
    def validate(self, graph: Dict[str, Any]) -> List[Dict[str, Any]]:
        return wf_schema.validate_graph(graph)

    # ── delete ─────────────────────────────────────────────────────────────
    def delete(self, workflow_id: str) -> Dict[str, Any]:
        wf = self._get(workflow_id)
        # Block deletion while ANY live agent version references it — even several
        # versions of the same agent (per-version copies must outlive their version).
        if self._configs_using(wf.id) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workflow is assigned to one or more agent versions. Unassign it first.",
            )
        wf.deleted_at = datetime.now(timezone.utc)
        self.db.commit()
        return {"success": True, "id": str(wf.id)}

    # ── Vapi import / export ───────────────────────────────────────────────
    def import_vapi(
        self,
        name: str,
        description: Optional[str],
        vapi_graph: Dict[str, Any],
        user_id: Optional[UUID],
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        canonical = vapi_adapter.from_vapi(vapi_graph or {})
        return self.create(
            name=name, description=description, user_id=user_id, graph=canonical, agent_id=agent_id
        )

    def export_vapi(self, workflow_id: str) -> Dict[str, Any]:
        wf = self._get(workflow_id)
        draft = self._version(wf.draft_version_id)
        graph = draft.graph if draft else wf_schema.empty_graph()
        return vapi_adapter.to_vapi(_mask_graph_secrets(graph))

    # ── helpers ────────────────────────────────────────────────────────────
    def _invalidate_assigned_agents(self, workflow_id: UUID) -> None:
        """Drop the pipeline cache for every agent assigned to this workflow."""
        try:
            from core.services.redis_service import cache_delete
        except Exception:
            return
        rows = (
            self.query(AgentConfig)
            .with_entities(AgentConfig.agent_id)
            .filter(AgentConfig.workflow_id == workflow_id, AgentConfig.deleted_at.is_(None))
            .distinct()
            .all()
        )
        for (agent_id,) in rows:
            try:
                cache_delete(f"agent_pipeline_config:{agent_id}")
            except Exception:
                pass
