'use client';

import '@xyflow/react/dist/style.css';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from 'next-themes';
import { useSetAtom } from 'jotai';
import {
  addEdge,
  Background,
  BackgroundVariant,
  Controls,
  MarkerType,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Connection,
  type EdgeChange,
  type NodeChange,
  type ReactFlowInstance,
} from '@xyflow/react';
import { Layers, Plus, Sparkles } from 'lucide-react';

import AppLoader from '@/components/shared/AppLoader';
import CustomButton from '@/components/shared/CustomButton';
import CustomDrawer from '@/components/shared/CustomDrawer';
import TextAreaField from '@/components/shared/TextAreaField';
import { showToast } from '@/utils/toast';
import { handleApiError } from '@/utils/helpers';
import {
  exportWorkflowAtom,
  fetchWorkflowAtom,
  publishWorkflowAtom,
  saveDraftAtom,
  workflowEditorStatusAtom,
  workflowIssuesAtom,
} from '@/atoms/WorkflowAtom';
import type {
  ConditionEdgeData,
  ValidationIssue,
  WorkflowEdge,
  WorkflowNode,
  WorkflowNodeType,
} from '@/types/workflow';
import { createNode, makeEdge, toCleanGraph, validateGraph } from '@/utils/workflowGraphUtils';
import { nodeTypes, NodeActionsContext } from '@/components/workflows/canvas/nodes';
import { edgeTypes, EdgeActionsContext } from '@/components/workflows/canvas/edges/ConditionEdge';
import NodePalette from '@/components/workflows/palette/NodePalette';
import NodeConfigDrawer from '@/components/workflows/config/NodeConfigDrawer';
import WorkflowToolbar from '@/components/workflows/WorkflowToolbar';

interface Props {
  workflowId: string;
}

/** One-tap building blocks for the global prompt drawer. */
const GLOBAL_PROMPT_SNIPPETS = [
  'Be warm, professional, and concise.',
  'Ask only one question at a time and wait for the answer.',
  'Always read key details back to confirm before acting.',
  'Never make up information you have not been given.',
];

const defaultEdgeOptions = {
  type: 'condition',
  markerEnd: { type: MarkerType.ArrowClosed },
} as const;

function isMeaningful(changes: NodeChange[] | EdgeChange[]): boolean {
  return changes.some((c) => {
    if (c.type === 'select') return false;
    if (c.type === 'position') return c.dragging === false;
    if (c.type === 'dimensions') return false;
    return true;
  });
}

function BuilderInner({ workflowId }: Props) {
  const router = useRouter();
  const { resolvedTheme } = useTheme();
  const { screenToFlowPosition, fitView, getNodes } = useReactFlow();

  const fetchWorkflow = useSetAtom(fetchWorkflowAtom);
  const saveDraft = useSetAtom(saveDraftAtom);
  const publish = useSetAtom(publishWorkflowAtom);
  const exportWorkflow = useSetAtom(exportWorkflowAtom);
  const setStatus = useSetAtom(workflowEditorStatusAtom);
  const setIssuesAtom = useSetAtom(workflowIssuesAtom);

  const [loading, setLoading] = useState(true);
  const [name, setName] = useState('');
  const [status, setWfStatus] = useState<'draft' | 'published'>('draft');
  const [globalPrompt, setGlobalPrompt] = useState('');
  const [globalOpen, setGlobalOpen] = useState(false);
  const artifactPlanRef = useRef<Record<string, unknown> | null>(null);
  const checksumRef = useRef<string | null>(null);
  const canvasRef = useRef<HTMLDivElement>(null);

  const [nodes, setNodes, onNodesChange] = useNodesState<WorkflowNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<WorkflowEdge>([]);
  const [issues, setIssues] = useState<ValidationIssue[]>([]);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [lastSavedAt, setLastSavedAt] = useState<number | null>(null);
  const [hasUnpublishedChanges, setHasUnpublishedChanges] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);

  // ── load ──
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const wf = await fetchWorkflow(workflowId);
        if (!active) return;
        setName(wf.name);
        setWfStatus(wf.status);
        setHasUnpublishedChanges(wf.has_unpublished_changes);
        setGlobalPrompt(wf.graph.globalPrompt ?? '');
        artifactPlanRef.current = wf.graph.artifactPlan ?? null;
        checksumRef.current = wf.graph_checksum;
        setNodes((wf.graph.nodes ?? []) as WorkflowNode[]);
        setEdges(
          ((wf.graph.edges ?? []) as WorkflowEdge[]).map((e) => ({ ...e, type: 'condition' })),
        );
      } catch (err) {
        handleApiError(err);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [workflowId, fetchWorkflow, setNodes, setEdges]);

  // ── validation (debounced) ──
  useEffect(() => {
    if (loading) return;
    const t = setTimeout(() => {
      const found = validateGraph(nodes, edges);
      setIssues(found);
      setIssuesAtom(found);
    }, 250);
    return () => clearTimeout(t);
  }, [nodes, edges, loading, setIssuesAtom]);

  useEffect(() => {
    setStatus({ dirty, saving });
  }, [dirty, saving, setStatus]);

  // Reset the shared editor atoms when leaving the editor so stale issues/status
  // don't leak into the next workflow opened.
  useEffect(
    () => () => {
      setIssuesAtom([]);
      setStatus({ dirty: false, saving: false });
    },
    [setIssuesAtom, setStatus],
  );

  // warn on unload while dirty
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (dirty) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [dirty]);

  // ── change handlers ──
  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      onNodesChange(changes as NodeChange<WorkflowNode>[]);
      if (isMeaningful(changes)) setDirty(true);
    },
    [onNodesChange],
  );
  const handleEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      onEdgesChange(changes as EdgeChange<WorkflowEdge>[]);
      if (isMeaningful(changes)) setDirty(true);
    },
    [onEdgesChange],
  );

  const onConnect = useCallback(
    (c: Connection) => {
      setEdges((eds) => addEdge(makeEdge(c.source!, c.target!), eds));
      setDirty(true);
    },
    [setEdges],
  );

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }, []);

  const addNodeAt = useCallback(
    (type: WorkflowNodeType, clientX?: number, clientY?: number) => {
      const position =
        clientX != null && clientY != null
          ? screenToFlowPosition({ x: clientX, y: clientY })
          : screenToFlowPosition({ x: window.innerWidth / 2, y: window.innerHeight / 2 });
      setNodes((nds) => nds.concat(createNode(type, position, nds)));
      setDirty(true);
    },
    [screenToFlowPosition, setNodes],
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const type = e.dataTransfer.getData('application/tone-node') as WorkflowNodeType;
      if (!type) return;
      addNodeAt(type, e.clientX, e.clientY);
    },
    [addNodeAt],
  );

  const updateNodeData = useCallback(
    (id: string, data: Record<string, unknown>) => {
      setNodes((nds) => nds.map((n) => (n.id === id ? { ...n, data } : n)));
      setDirty(true);
    },
    [setNodes],
  );

  const updateEdgeData = useCallback(
    (id: string, data: ConditionEdgeData) => {
      setEdges((eds) => eds.map((e) => (e.id === id ? { ...e, data } : e)));
      setDirty(true);
    },
    [setEdges],
  );

  const deleteNode = useCallback(
    (id: string) => {
      setNodes((nds) => nds.filter((n) => n.id !== id));
      setEdges((eds) => eds.filter((e) => e.source !== id && e.target !== id));
      setSelectedNodeId(null);
      setDirty(true);
    },
    [setNodes, setEdges],
  );

  const deleteEdge = useCallback(
    (id: string) => {
      setEdges((eds) => eds.filter((e) => e.id !== id));
      setSelectedEdgeId((cur) => (cur === id ? null : cur));
      setDirty(true);
    },
    [setEdges],
  );

  const edgeActions = useMemo(
    () => ({
      onEdit: (id: string) => {
        setSelectedEdgeId(id);
        setSelectedNodeId(null);
      },
      onDelete: deleteEdge,
    }),
    [deleteEdge],
  );

  const nodeActions = useMemo(() => ({ onDelete: deleteNode }), [deleteNode]);

  // ── save / publish ──
  const buildGraph = useCallback(
    () => toCleanGraph(getNodes() as WorkflowNode[], edges, globalPrompt, artifactPlanRef.current),
    [getNodes, edges, globalPrompt],
  );

  const handleSave = useCallback(async () => {
    if (saving) return;
    setSaving(true);
    const sent = buildGraph();
    const sentJson = JSON.stringify(sent);
    try {
      const detail = await saveDraft({
        workflowId,
        graph: sent,
        expectedChecksum: checksumRef.current,
      });
      checksumRef.current = detail.graph_checksum;
      setHasUnpublishedChanges(detail.has_unpublished_changes);
      // Only mark clean if nothing was edited during the in-flight save — otherwise the
      // newest edits would be silently shown as "saved".
      if (JSON.stringify(buildGraph()) === sentJson) setDirty(false);
      setLastSavedAt(Date.now());
      showToast.success('Draft saved');
    } catch (err) {
      handleApiError(err);
    } finally {
      setSaving(false);
    }
  }, [buildGraph, saveDraft, workflowId, saving]);

  const handlePublish = useCallback(async () => {
    if (saving) return; // avoid double-submit / checksum conflict with an in-flight save
    setSaving(true);
    const sent = buildGraph();
    const sentJson = JSON.stringify(sent);
    try {
      await saveDraft({ workflowId, graph: sent, expectedChecksum: checksumRef.current });
      const detail = await publish(workflowId);
      checksumRef.current = detail.graph_checksum;
      setWfStatus(detail.status);
      setHasUnpublishedChanges(detail.has_unpublished_changes);
      if (JSON.stringify(buildGraph()) === sentJson) setDirty(false);
      setLastSavedAt(Date.now());
      showToast.success(
        'Workflow published',
        'Assigned agents will use the new graph on the next call.',
      );
    } catch (err) {
      handleApiError(err);
    } finally {
      setSaving(false);
    }
  }, [buildGraph, publish, saveDraft, workflowId, saving]);

  const handleExport = useCallback(async () => {
    try {
      const vapi = await exportWorkflow(workflowId);
      const blob = new Blob([JSON.stringify(vapi, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${(name || 'workflow').replace(/\s+/g, '-').toLowerCase()}.vapi.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      handleApiError(err);
    }
  }, [exportWorkflow, workflowId, name]);

  const focusNode = useCallback(
    (nodeName: string) => {
      const node = getNodes().find((n) => n.id === nodeName);
      if (node) fitView({ nodes: [{ id: node.id }], duration: 400, padding: 0.5 });
    },
    [fitView, getNodes],
  );

  // Default view: 100% zoom, content centered horizontally and pinned near the top
  // (so a fresh single-node workflow doesn't get blown up by fitView). Falls back to
  // a zoom-clamped fitView when the graph is too large to fit at 1×.
  const positionInitialView = useCallback(
    (instance: ReactFlowInstance<WorkflowNode, WorkflowEdge>) => {
      const rf = instance.getNodes();
      if (!rf.length) return;
      const W = canvasRef.current?.clientWidth ?? 0;
      const H = canvasRef.current?.clientHeight ?? 0;
      const w = (n: (typeof rf)[number]) => n.measured?.width ?? 268;
      const h = (n: (typeof rf)[number]) => n.measured?.height ?? 120;
      const minX = Math.min(...rf.map((n) => n.position.x));
      const maxX = Math.max(...rf.map((n) => n.position.x + w(n)));
      const minY = Math.min(...rf.map((n) => n.position.y));
      const maxY = Math.max(...rf.map((n) => n.position.y + h(n)));
      const fitsAtFullZoom = W > 0 && maxX - minX <= W * 0.9 && maxY - minY <= H * 0.8;
      if (fitsAtFullZoom) {
        instance.setViewport({ x: W / 2 - (minX + maxX) / 2, y: 72 - minY, zoom: 1 });
      } else {
        instance.fitView({ maxZoom: 1, padding: 0.2 });
      }
    },
    [],
  );

  const selectedNode = useMemo(
    () => nodes.find((n) => n.id === selectedNodeId) ?? null,
    [nodes, selectedNodeId],
  );
  const selectedEdge = useMemo(
    () => edges.find((e) => e.id === selectedEdgeId) ?? null,
    [edges, selectedEdgeId],
  );

  if (loading) return <AppLoader />;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <WorkflowToolbar
        name={name}
        status={status}
        saving={saving}
        dirty={dirty}
        hasUnpublishedChanges={hasUnpublishedChanges}
        lastSavedAt={lastSavedAt}
        issues={issues}
        onBack={() => router.push('/workflows')}
        onSave={handleSave}
        onPublish={handlePublish}
        onOpenGlobalPrompt={() => setGlobalOpen(true)}
        onExport={handleExport}
        onFocusNode={focusNode}
      />

      <div className="flex min-h-0 flex-1">
        <div
          ref={canvasRef}
          className="workflow-canvas relative min-h-0 flex-1"
          tabIndex={0}
          role="application"
          aria-label="Workflow canvas. Select a node or edge and press Enter to edit it."
          onDrop={onDrop}
          onDragOver={onDragOver}
          onKeyDown={(e) => {
            // Keyboard access: Enter opens the config drawer for the selected node/edge.
            if (e.key !== 'Enter') return;
            const selNode = getNodes().find((n) => n.selected);
            if (selNode) {
              setSelectedNodeId(selNode.id);
              setSelectedEdgeId(null);
              return;
            }
            const selEdge = edges.find((ed) => ed.selected);
            if (selEdge) {
              setSelectedEdgeId(selEdge.id);
              setSelectedNodeId(null);
            }
          }}
        >
          <NodeActionsContext.Provider value={nodeActions}>
            <EdgeActionsContext.Provider value={edgeActions}>
              <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={handleNodesChange}
                onEdgesChange={handleEdgesChange}
                onConnect={onConnect}
                nodeTypes={nodeTypes}
                edgeTypes={edgeTypes}
                defaultEdgeOptions={defaultEdgeOptions}
                colorMode={(resolvedTheme as 'light' | 'dark') ?? 'light'}
                nodesDraggable
                nodeDragThreshold={1}
                connectionRadius={48}
                isValidConnection={(c) => c.source !== c.target}
                onNodeDoubleClick={(_, n) => {
                  setSelectedNodeId(n.id);
                  setSelectedEdgeId(null);
                }}
                onEdgeClick={(_, e) => {
                  setSelectedEdgeId(e.id);
                  setSelectedNodeId(null);
                }}
                onPaneClick={() => {
                  setSelectedNodeId(null);
                  setSelectedEdgeId(null);
                }}
                proOptions={{ hideAttribution: true }}
                onInit={positionInitialView}
                minZoom={0.2}
              >
                <Background variant={BackgroundVariant.Dots} gap={22} size={1.4} />
                <Controls className="!shadow-md" showInteractive={false} />
              </ReactFlow>
            </EdgeActionsContext.Provider>
          </NodeActionsContext.Provider>

          {/* interaction hint */}
          <div className="pointer-events-none absolute bottom-5 left-1/2 z-10 -translate-x-1/2">
            <span className="rounded-full border border-border bg-card/70 px-3 py-1 text-[11px] text-muted-foreground shadow-sm backdrop-blur">
              Drag to move · double-click a node to edit · click an edge to set its condition
            </span>
          </div>
        </div>

        <NodePalette onAdd={(t) => addNodeAt(t)} />
      </div>

      <NodeConfigDrawer
        node={selectedNode}
        edge={selectedEdge}
        onClose={() => {
          setSelectedNodeId(null);
          setSelectedEdgeId(null);
        }}
        onChangeNode={updateNodeData}
        onChangeEdge={updateEdgeData}
        onDeleteNode={deleteNode}
      />

      <CustomDrawer
        open={globalOpen}
        onClose={() => setGlobalOpen(false)}
        side="right"
        width="w-[440px] sm:max-w-[440px]"
        title="Global prompt"
        description="Applied to every node, layered above the agent persona and each node's prompt."
        footer={
          <div className="flex justify-end">
            <CustomButton type="primary" size="sm" onClick={() => setGlobalOpen(false)}>
              Done
            </CustomButton>
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          {/* layered-prompt explainer */}
          <div className="rounded-xl border border-border bg-muted/40 p-3.5">
            <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
              <Layers className="h-3.5 w-3.5 text-primary" />
              How prompts apply
            </div>
            <p className="mt-1.5 text-[12px] text-muted-foreground">
              In workflow mode the workflow drives the call on its own — the agent&apos;s system
              prompt is not used. Set the call-wide persona and tone here.
            </p>
            <ol className="mt-2.5 space-y-1.5 text-[12px] text-muted-foreground">
              <li className="flex items-start gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                <span>
                  <span className="font-medium text-foreground/80">Global prompt</span> — this text,
                  applied to every node.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-muted-foreground/40" />
                <span>
                  <span className="font-medium text-foreground/80">Node prompt</span> — what to do
                  at each step.
                </span>
              </li>
            </ol>
          </div>

          <TextAreaField
            name="global-prompt"
            label="Global instructions"
            rows={10}
            maxLength={4000}
            placeholder="e.g. Be calm, warm, and concise. Always read details back to confirm before acting."
            helperText="Keep it about call-wide tone and rules — leave step-specific instructions to each node."
            value={globalPrompt}
            onChange={(e) => {
              setGlobalPrompt(e.target.value);
              setDirty(true);
            }}
          />

          <div className="-mt-1 flex items-center justify-between">
            <span className="text-[11px] text-muted-foreground">
              Use <code className="font-mono text-foreground/70">{'{{variables}}'}</code> to insert
              collected values.
            </span>
            <span className="font-mono text-[11px] text-muted-foreground">
              {globalPrompt.length}/4000
            </span>
          </div>

          {/* quick starters */}
          <div>
            <div className="mb-2 flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              <Sparkles className="h-3 w-3" />
              Quick add
            </div>
            <div className="flex flex-wrap gap-1.5">
              {GLOBAL_PROMPT_SNIPPETS.map((snippet) => (
                <CustomButton
                  key={snippet}
                  type="default"
                  size="xs"
                  icon={<Plus className="h-3 w-3" />}
                  onClick={() => {
                    setGlobalPrompt((prev) =>
                      prev.trim() ? `${prev.trim()}\n${snippet}` : snippet,
                    );
                    setDirty(true);
                  }}
                  className="!h-auto whitespace-normal py-1 text-left text-[11px] font-normal"
                >
                  {snippet}
                </CustomButton>
              ))}
            </div>
          </div>
        </div>
      </CustomDrawer>
    </div>
  );
}

const WorkflowBuilder: React.FC<Props> = ({ workflowId }) => (
  <ReactFlowProvider>
    <BuilderInner workflowId={workflowId} />
  </ReactFlowProvider>
);

export default WorkflowBuilder;
