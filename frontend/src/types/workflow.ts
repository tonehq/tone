import type { Edge, Node } from '@xyflow/react';

// ── node types ──────────────────────────────────────────────────────────────
export type WorkflowNodeType =
  | 'conversation'
  | 'decision'
  | 'tool'
  | 'transferCall'
  | 'endCall'
  | 'apiRequest';

export type EdgeConditionType = 'ai' | 'logic';

// Node `data` is intentionally an open record on the wire (React Flow renders it directly
// and the editor reads fields by key). The authoritative per-type field set lives in the
// backend schema (`core/services/workflow/schema.py`) and serializer; nodes are kept as a
// generic record here so the canonical graph round-trips without a transform.
export type WorkflowNode = Node<Record<string, unknown>, WorkflowNodeType>;

export interface ConditionEdgeData extends Record<string, unknown> {
  condition: { type: EdgeConditionType; prompt: string };
}
export type WorkflowEdge = Edge<ConditionEdgeData>;

// ── graph (canonical, React-Flow-native) ─────────────────────────────────────
export interface WorkflowGraph {
  schemaVersion: number;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  globalPrompt: string;
  artifactPlan: Record<string, unknown> | null;
}

// ── API payloads ─────────────────────────────────────────────────────────────
export interface ValidationIssue {
  code: string;
  node_name: string | null;
  message: string;
}

export interface WorkflowSummary {
  id: string;
  name: string;
  description: string | null;
  is_valid: boolean;
  agents_using: number;
  /** Owning agent (null for legacy org-level workflows). */
  agent_id?: string | null;
  /** Agent version numbers whose live configs reference this workflow. */
  assigned_versions?: number[];
  updated_at: string | null;
}

export interface WorkflowDetail {
  id: string;
  name: string;
  description: string | null;
  agents_using: number;
  agent_id?: string | null;
  assigned_versions?: number[];
  draft_version_id: string | null;
  graph: WorkflowGraph;
  graph_checksum: string | null;
  is_valid: boolean;
  validation_errors: ValidationIssue[];
  created_at: string | null;
  updated_at: string | null;
}
