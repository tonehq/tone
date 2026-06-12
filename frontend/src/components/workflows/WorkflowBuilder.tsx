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
} from '@xyflow/react';
import { FileDown, Settings2 } from 'lucide-react';

import AppLoader from '@/components/shared/AppLoader';
import CustomButton from '@/components/shared/CustomButton';
import CustomDrawer from '@/components/shared/CustomDrawer';
import { showToast } from '@/utils/toast';
import { handleApiError } from '@/utils/helpers';
import {
  fetchWorkflowAtom,
  publishWorkflowAtom,
  saveDraftAtom,
  workflowEditorStatusAtom,
} from '@/atoms/WorkflowAtom';
import type {
  ConditionEdgeData,
  ValidationIssue,
  WorkflowEdge,
  WorkflowNode,
  WorkflowNodeType,
} from '@/types/workflow';
import { createNode, makeEdge, toCleanGraph, validateGraph } from '@/utils/workflowGraphUtils';
import { nodeTypes } from '@/components/workflows/canvas/nodes';
import { edgeTypes } from '@/components/workflows/canvas/edges/ConditionEdge';
import NodePalette from '@/components/workflows/palette/NodePalette';
import NodeConfigDrawer from '@/components/workflows/config/NodeConfigDrawer';
import WorkflowToolbar from '@/components/workflows/WorkflowToolbar';

interface Props {
  workflowId: string;
}

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
  const setStatus = useSetAtom(workflowEditorStatusAtom);

  const [loading, setLoading] = useState(true);
  const [name, setName] = useState('');
  const [status, setWfStatus] = useState<'draft' | 'published'>('draft');
  const [globalPrompt, setGlobalPrompt] = useState('');
  const [globalOpen, setGlobalOpen] = useState(false);
  const artifactPlanRef = useRef<Record<string, unknown> | null>(null);
  const checksumRef = useRef<string | null>(null);

  const [nodes, setNodes, onNodesChange] = useNodesState<WorkflowNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<WorkflowEdge>([]);
  const [issues, setIssues] = useState<ValidationIssue[]>([]);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [lastSavedAt, setLastSavedAt] = useState<number | null>(null);
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
      setStatus((s) => ({ ...s, issues: found }));
    }, 250);
    return () => clearTimeout(t);
  }, [nodes, edges, loading, setStatus]);

  useEffect(() => {
    setStatus((s) => ({ ...s, dirty, saving }));
  }, [dirty, saving, setStatus]);

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

  // ── save / publish ──
  const buildGraph = useCallback(
    () => toCleanGraph(getNodes() as WorkflowNode[], edges, globalPrompt, artifactPlanRef.current),
    [getNodes, edges, globalPrompt],
  );

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      const detail = await saveDraft({
        workflowId,
        graph: buildGraph(),
        expectedChecksum: checksumRef.current,
      });
      checksumRef.current = detail.graph_checksum;
      setDirty(false);
      setLastSavedAt(Date.now());
      showToast.success('Draft saved');
    } catch (err) {
      handleApiError(err);
    } finally {
      setSaving(false);
    }
  }, [buildGraph, saveDraft, workflowId]);

  const handlePublish = useCallback(async () => {
    setSaving(true);
    try {
      await saveDraft({ workflowId, graph: buildGraph(), expectedChecksum: checksumRef.current });
      const detail = await publish(workflowId);
      checksumRef.current = detail.graph_checksum;
      setWfStatus(detail.status);
      setDirty(false);
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
  }, [buildGraph, publish, saveDraft, workflowId]);

  const focusNode = useCallback(
    (nodeName: string) => {
      const node = getNodes().find((n) => n.id === nodeName);
      if (node) fitView({ nodes: [{ id: node.id }], duration: 400, padding: 0.5 });
    },
    [fitView, getNodes],
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
        lastSavedAt={lastSavedAt}
        issues={issues}
        onBack={() => router.push('/workflows')}
        onSave={handleSave}
        onPublish={handlePublish}
        onFocusNode={focusNode}
      />

      <div className="flex min-h-0 flex-1">
        <div
          className="workflow-canvas relative min-h-0 flex-1"
          onDrop={onDrop}
          onDragOver={onDragOver}
        >
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
            onNodeClick={(_, n) => {
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
            fitView
          >
            <Background variant={BackgroundVariant.Dots} gap={22} size={1.4} />
            <Controls className="!shadow-md" showInteractive={false} />
          </ReactFlow>

          {/* bottom-left utility bar */}
          <div className="pointer-events-none absolute bottom-4 left-4 z-10 flex gap-2">
            <CustomButton
              type="default"
              size="sm"
              icon={<Settings2 className="h-4 w-4" />}
              onClick={() => setGlobalOpen(true)}
              className="pointer-events-auto !bg-card/90 !backdrop-blur"
            >
              Global prompt
            </CustomButton>
            <CustomButton
              type="text"
              size="sm"
              icon={<FileDown className="h-4 w-4" />}
              onClick={() =>
                window.open(`/api/v1/workflow/export_vapi?workflow_id=${workflowId}`, '_blank')
              }
              className="pointer-events-auto !bg-card/90 !backdrop-blur"
            >
              Export
            </CustomButton>
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
        <textarea
          className="min-h-[200px] w-full resize-y rounded-md border border-border bg-background px-2.5 py-2 text-sm outline-none ring-primary/40 focus:ring-2"
          placeholder="e.g. Be calm, warm, and concise. Always read details back to confirm."
          value={globalPrompt}
          onChange={(e) => {
            setGlobalPrompt(e.target.value);
            setDirty(true);
          }}
        />
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
