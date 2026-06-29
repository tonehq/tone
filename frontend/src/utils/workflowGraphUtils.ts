import type {
  ConditionEdgeData,
  ValidationIssue,
  WorkflowEdge,
  WorkflowGraph,
  WorkflowNode,
  WorkflowNodeType,
} from '@/types/workflow';
import { NODE_REGISTRY } from '@/components/workflows/nodeRegistry';

const TERMINAL = new Set<WorkflowNodeType>(['endCall', 'transferCall']);

export function defaultGraph(): WorkflowGraph {
  return {
    schemaVersion: 1,
    nodes: [
      {
        id: 'start',
        type: 'conversation',
        position: { x: 0, y: 0 },
        data: {
          name: 'start',
          isStart: true,
          prompt: 'Greet the caller and ask how you can help.',
          messagePlan: { firstMessage: 'Hi! How can I help you today?' },
          variableExtractionPlan: { output: [] },
          toolIds: [],
        },
      } as unknown as WorkflowNode,
    ],
    edges: [],
    globalPrompt: '',
    artifactPlan: null,
  };
}

/** Generate a unique node id/name for a new node of the given type. */
export function nextNodeId(type: WorkflowNodeType, existing: WorkflowNode[]): string {
  const taken = new Set(existing.map((n) => n.id));
  let i = 1;
  let id = `${type}_${i}`;
  while (taken.has(id)) {
    i += 1;
    id = `${type}_${i}`;
  }
  return id;
}

export function createNode(
  type: WorkflowNodeType,
  position: { x: number; y: number },
  existing: WorkflowNode[],
): WorkflowNode {
  const id = nextNodeId(type, existing);
  const meta = NODE_REGISTRY[type];
  return {
    id,
    type,
    position,
    data: { name: id, ...meta.defaultData() },
  } as unknown as WorkflowNode;
}

export function makeEdge(source: string, target: string): WorkflowEdge {
  return {
    id: `${source}->${target}`,
    source,
    target,
    type: 'condition',
    data: { condition: { type: 'ai', prompt: '' } } as ConditionEdgeData,
  } as WorkflowEdge;
}

/** Strip React-Flow runtime-injected fields so persisted JSON stays clean. */
export function toCleanGraph(
  nodes: WorkflowNode[],
  edges: WorkflowEdge[],
  globalPrompt: string,
  artifactPlan: Record<string, unknown> | null = null,
): WorkflowGraph {
  return {
    schemaVersion: 1,
    nodes: nodes.map((n) => ({
      id: n.id,
      type: n.type,
      position: { x: Math.round(n.position.x), y: Math.round(n.position.y) },
      data: n.data,
    })) as WorkflowNode[],
    edges: edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      type: 'condition',
      data: (e.data ?? { condition: { type: 'ai', prompt: '' } }) as ConditionEdgeData,
    })) as WorkflowEdge[],
    globalPrompt,
    artifactPlan,
  };
}

/** Client-side validation mirroring the backend's WorkflowService.validate. */
export function validateGraph(nodes: WorkflowNode[], edges: WorkflowEdge[]): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  if (nodes.length === 0) {
    issues.push({ code: 'EMPTY', node_name: null, message: 'Workflow has no nodes.' });
    return issues;
  }

  const ids = nodes.map((n) => n.id);
  const idSet = new Set(ids);

  const starts = nodes.filter((n) => (n.data as { isStart?: boolean }).isStart);
  if (starts.length === 0)
    issues.push({
      code: 'NO_START',
      node_name: null,
      message: 'No start node — mark the entry node as Start.',
    });
  else if (starts.length > 1)
    starts.forEach((n) =>
      issues.push({
        code: 'MULTIPLE_START',
        node_name: n.id,
        message: 'More than one start node.',
      }),
    );

  const out: Record<string, number> = Object.fromEntries(ids.map((id) => [id, 0]));
  edges.forEach((e) => {
    if (!idSet.has(e.source))
      issues.push({
        code: 'DANGLING_EDGE',
        node_name: e.source,
        message: 'Edge from a missing node.',
      });
    if (!idSet.has(e.target))
      issues.push({
        code: 'DANGLING_EDGE',
        node_name: e.target,
        message: 'Edge to a missing node.',
      });
    if (e.source in out) out[e.source] += 1;
  });

  const globalIds = new Set(
    nodes.filter((n) => (n.data as { isGlobal?: boolean }).isGlobal).map((n) => n.id),
  );
  nodes.forEach((n) => {
    const terminal = TERMINAL.has(n.type as WorkflowNodeType);
    if (terminal && out[n.id] > 0)
      issues.push({
        code: 'TERMINAL_OUTGOING',
        node_name: n.id,
        message: 'Terminal node must not have outgoing edges.',
      });
    if (!terminal && out[n.id] === 0 && !globalIds.has(n.id))
      issues.push({ code: 'DEAD_END', node_name: n.id, message: 'Node has no outgoing edge.' });
  });

  if (starts.length === 1) {
    const adj: Record<string, string[]> = Object.fromEntries(ids.map((id) => [id, []]));
    edges.forEach((e) => {
      if (e.source in adj && idSet.has(e.target)) adj[e.source].push(e.target);
    });
    const reachable = new Set<string>(globalIds);
    const stack = [starts[0].id];
    while (stack.length) {
      const cur = stack.pop() as string;
      if (reachable.has(cur)) continue;
      reachable.add(cur);
      (adj[cur] ?? []).forEach((t) => stack.push(t));
    }
    ids.forEach((id) => {
      if (!reachable.has(id))
        issues.push({
          code: 'UNREACHABLE',
          node_name: id,
          message: 'Not reachable from the start node.',
        });
    });
    const typeMap = Object.fromEntries(nodes.map((n) => [n.id, n.type]));
    const hasTerminal = [...reachable].some((id) => TERMINAL.has(typeMap[id] as WorkflowNodeType));
    if (!hasTerminal)
      issues.push({
        code: 'NO_TERMINAL',
        node_name: null,
        message: 'No reachable End/Transfer node — the call can never end.',
      });
  }

  return issues;
}

// ── Vapi import/export (client mirror of the backend adapter) ────────────────
export function fromVapi(vapi: Record<string, unknown>): WorkflowGraph {
  const vNodes = (vapi.nodes as Record<string, unknown>[]) ?? [];
  const seenNodeIds = new Set<string>();
  const nodes = vNodes.map((vn, idx) => {
    const node = { ...vn };
    let name = (node.name as string) || (node.id as string) || `node_${idx}`;
    // De-dupe ids so two Vapi nodes sharing a name don't collide (mirrors the edge de-dupe).
    if (seenNodeIds.has(name)) {
      let i = 1;
      while (seenNodeIds.has(`${name}#${i}`)) i += 1;
      name = `${name}#${i}`;
    }
    seenNodeIds.add(name);
    const type = (node.type as WorkflowNodeType) ?? 'conversation';
    const metadata = (node.metadata as { position?: { x: number; y: number } }) ?? {};
    const position = metadata.position ?? { x: 0, y: 0 };
    delete (node as Record<string, unknown>).type;
    delete (node as Record<string, unknown>).metadata;
    delete (node as Record<string, unknown>).id;
    return {
      id: name,
      type,
      position: { x: position.x ?? 0, y: position.y ?? 0 },
      data: { ...node, name },
    } as unknown as WorkflowNode;
  });

  const seen = new Set<string>();
  const edges = ((vapi.edges as Record<string, unknown>[]) ?? [])
    .filter((e) => e.from && e.to)
    .map((e) => {
      const src = e.from as string;
      const tgt = e.to as string;
      let id = `${src}->${tgt}`;
      let i = 1;
      while (seen.has(id)) id = `${src}->${tgt}#${i++}`;
      seen.add(id);
      return {
        id,
        source: src,
        target: tgt,
        type: 'condition',
        data: {
          condition: (e.condition as ConditionEdgeData['condition']) ?? { type: 'ai', prompt: '' },
        },
      } as WorkflowEdge;
    });

  return {
    schemaVersion: 1,
    nodes,
    edges,
    globalPrompt: (vapi.globalPrompt as string) ?? '',
    artifactPlan: (vapi.artifactPlan as Record<string, unknown>) ?? null,
  };
}
