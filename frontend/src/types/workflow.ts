import type { Edge, Node } from '@xyflow/react';

// ── node types ──────────────────────────────────────────────────────────────
export type WorkflowNodeType = 'conversation' | 'decision' | 'tool' | 'transferCall' | 'endCall';

export type EdgeConditionType = 'ai' | 'logic';

export interface MessagePlan {
  firstMessage?: string;
}

export interface ExtractVar {
  title: string;
  type: string; // string | number | boolean | date
  enum: string[];
  description: string;
}

export interface VariableExtractionPlan {
  output: ExtractVar[];
}

export interface InlineTool {
  type: string; // endCall | transferCall | sms
}

// ── per-type node data (discriminated by the node's `type`) ──────────────────
interface BaseNodeData {
  name: string;
  isStart?: boolean;
  isGlobal?: boolean;
  condition?: string; // enter-condition (Liquid) for a global node
}

export interface ConversationData extends BaseNodeData {
  kind: 'conversation';
  prompt?: string;
  messagePlan?: MessagePlan;
  variableExtractionPlan?: VariableExtractionPlan;
  toolIds?: string[];
  maxVisits?: number;
}

export interface DecisionData extends BaseNodeData {
  kind: 'decision';
  prompt?: string;
}

export interface ToolData extends BaseNodeData {
  kind: 'tool';
  toolId?: string;
  tool?: InlineTool;
}

export interface TransferCallData extends BaseNodeData {
  kind: 'transferCall';
  destination?: Record<string, unknown>;
  transferPlan?: Record<string, unknown>;
  messagePlan?: MessagePlan;
}

export interface EndCallData extends BaseNodeData {
  kind: 'endCall';
  messagePlan?: MessagePlan;
}

// `kind` is a client-only discriminant mirroring the node `type`, kept off the wire.
export type WorkflowNodeData =
  | ConversationData
  | DecisionData
  | ToolData
  | TransferCallData
  | EndCallData;

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
  status: 'draft' | 'published';
  is_valid: boolean;
  agents_using: number;
  updated_at: string | null;
}

export interface WorkflowDetail {
  id: string;
  name: string;
  description: string | null;
  status: 'draft' | 'published';
  agents_using: number;
  draft_version_id: string | null;
  published_version_id: string | null;
  latest_version: number;
  graph: WorkflowGraph;
  graph_checksum: string | null;
  is_valid: boolean;
  validation_errors: ValidationIssue[];
  has_published: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface WorkflowVersionSummary {
  id: string;
  version: number;
  is_live: boolean;
  published_at: string | null;
}
