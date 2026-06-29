'use client';

import React, { useEffect, useMemo } from 'react';
import { useAtomValue, useSetAtom } from 'jotai';
import { Plus, Trash2 } from 'lucide-react';

import { cn } from '@/utils/cn';
import CustomDrawer from '@/components/shared/CustomDrawer';
import CustomButton from '@/components/shared/CustomButton';
import TextInput from '@/components/shared/TextInput';
import TextAreaField from '@/components/shared/TextAreaField';
import CheckboxField from '@/components/shared/CheckboxField';
import SelectInput from '@/components/shared/SelectInput';
import SearchableSelect from '@/components/shared/SearchableSelect';
import { fetchToolsAtom, toolsAtom } from '@/atoms/ToolAtom';
import { NODE_REGISTRY } from '@/components/workflows/nodeRegistry';
import type {
  ConditionEdgeData,
  EdgeConditionType,
  WorkflowEdge,
  WorkflowNode,
  WorkflowNodeType,
} from '@/types/workflow';

type D = Record<string, unknown>;

/** Variable value types the extractor supports. */
const VAR_TYPE_OPTIONS = [
  { value: 'string', label: 'Text' },
  { value: 'number', label: 'Number' },
  { value: 'boolean', label: 'Yes / No' },
  { value: 'date', label: 'Date' },
];

interface Props {
  node: WorkflowNode | null;
  edge: WorkflowEdge | null;
  onClose: () => void;
  onChangeNode: (id: string, data: D) => void;
  onChangeEdge: (id: string, data: ConditionEdgeData) => void;
  onDeleteNode: (id: string) => void;
}

// ── layout primitives ─────────────────────────────────────────────────────────
const SectionTitle: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="mb-2 font-mono text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
    {children}
  </div>
);

const Card: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className,
}) => (
  <div className={cn('rounded-lg border border-border bg-muted/30 p-3', className)}>{children}</div>
);

const NodeConfigDrawer: React.FC<Props> = ({
  node,
  edge,
  onClose,
  onChangeNode,
  onChangeEdge,
  onDeleteNode,
}) => {
  const open = Boolean(node || edge);
  const { tools, loading: toolsLoading } = useAtomValue(toolsAtom);
  const fetchTools = useSetAtom(fetchToolsAtom);

  const isToolNode = node?.type === 'tool';
  useEffect(() => {
    if (isToolNode && tools.length === 0 && !toolsLoading) fetchTools();
  }, [isToolNode, tools.length, toolsLoading, fetchTools]);

  const toolOptions = useMemo(() => tools.map((t) => ({ value: t.id, label: t.name })), [tools]);

  // ── node editing ──
  const renderNode = () => {
    if (!node) return null;
    const type = node.type as WorkflowNodeType;
    const meta = NODE_REGISTRY[type];
    const Icon = meta.icon;
    const data = node.data as D;
    const patch = (p: D) => onChangeNode(node.id, { ...data, ...p });
    const fm = String((data.messagePlan as D | undefined)?.firstMessage ?? '');
    const setFirstMessage = (v: string) =>
      patch({ messagePlan: { ...(data.messagePlan as D), firstMessage: v } });

    const vars = ((data.variableExtractionPlan as D | undefined)?.output as D[] | undefined) ?? [];
    const setVars = (next: D[]) => patch({ variableExtractionPlan: { output: next } });

    return (
      <div className="flex flex-col gap-5">
        {/* identity */}
        <div>
          <div className="mb-2.5 flex items-center gap-2.5">
            <span
              className={cn(
                'inline-flex h-9 w-9 items-center justify-center rounded-lg',
                meta.accent.chip,
              )}
            >
              <Icon className="h-4.5 w-4.5" />
            </span>
            <span className="font-mono text-[11px] uppercase tracking-wide text-muted-foreground">
              {meta.label} node
            </span>
          </div>
          <TextInput
            name="node-name"
            label="Node name"
            value={String(data.name ?? node.id)}
            onChange={(e) => patch({ name: e.target.value })}
            placeholder="e.g. collect_name"
          />
        </div>

        {/* conversation: first message */}
        {(type === 'conversation' || type === 'transferCall' || type === 'endCall') && (
          <TextAreaField
            name="first-message"
            label={
              type === 'endCall'
                ? 'Goodbye message'
                : type === 'transferCall'
                  ? 'Message before transfer'
                  : 'First message (spoken on entry)'
            }
            rows={type === 'conversation' ? 2 : 3}
            value={fm}
            onChange={(e) => setFirstMessage(e.target.value)}
            placeholder="What the agent says when it reaches this node…"
          />
        )}

        {/* conversation / decision: prompt */}
        {(type === 'conversation' || type === 'decision') && (
          <TextAreaField
            name="prompt"
            label={type === 'decision' ? 'Routing guidance (optional)' : 'Prompt'}
            rows={5}
            value={String(data.prompt ?? '')}
            onChange={(e) => patch({ prompt: e.target.value })}
            placeholder={
              type === 'decision'
                ? 'Optional hint for AI-routed branches'
                : 'What should the agent do at this step? Use {{variables}} for dynamic values.'
            }
            helperText="The LLM (model & temperature) is inherited from the assigned agent."
          />
        )}

        {/* tool */}
        {type === 'tool' && (
          <SearchableSelect
            name="tool"
            label="Tool"
            options={toolOptions}
            value={String(data.toolId ?? '')}
            onValueChange={(v) => patch({ toolId: v, tool: undefined })}
            loading={toolsLoading}
            placeholder="Select a tool (webhook / custom / MCP)"
          />
        )}

        {/* transfer destination */}
        {type === 'transferCall' && (
          <TextInput
            name="destination"
            label="Destination number"
            value={String((data.destination as D | undefined)?.number ?? '')}
            onChange={(e) => patch({ destination: { type: 'number', number: e.target.value } })}
            placeholder="+15551234567"
            className="font-mono"
          />
        )}

        {/* extract variables */}
        {type === 'conversation' && (
          <div>
            <div className="mb-2 flex items-center justify-between">
              <SectionTitle>Extract variables</SectionTitle>
              <CustomButton
                type="text"
                size="xs"
                icon={<Plus className="h-3.5 w-3.5" />}
                onClick={() =>
                  setVars([...vars, { title: '', type: 'string', enum: [], description: '' }])
                }
              >
                Add
              </CustomButton>
            </div>
            {vars.length === 0 ? (
              <Card className="text-xs text-muted-foreground">
                No variables extracted here. Add one to capture what the caller says (e.g.{' '}
                <span className="font-mono">customer_name</span>).
              </Card>
            ) : (
              <div className="flex flex-col gap-2.5">
                {vars.map((v, i) => (
                  <Card key={i} className="bg-card">
                    <div className="flex items-start gap-2">
                      <div className="flex flex-1 flex-col gap-2">
                        <div className="flex items-center gap-2">
                          <TextInput
                            name={`var-name-${i}`}
                            value={String(v.title ?? '')}
                            onChange={(e) =>
                              setVars(
                                vars.map((x, j) => (j === i ? { ...x, title: e.target.value } : x)),
                              )
                            }
                            placeholder="variable_name"
                            className="flex-1 font-mono"
                          />
                          <SelectInput
                            name={`var-type-${i}`}
                            options={VAR_TYPE_OPTIONS}
                            value={String(v.type ?? 'string')}
                            onValueChange={(val) =>
                              setVars(vars.map((x, j) => (j === i ? { ...x, type: val } : x)))
                            }
                            className="w-28 shrink-0"
                          />
                        </div>
                        <TextInput
                          name={`var-desc-${i}`}
                          value={String(v.description ?? '')}
                          onChange={(e) =>
                            setVars(
                              vars.map((x, j) =>
                                j === i ? { ...x, description: e.target.value } : x,
                              ),
                            )
                          }
                          placeholder="What to capture (description)"
                        />
                      </div>
                      <CustomButton
                        type="text"
                        size="icon-sm"
                        aria-label="Remove variable"
                        onClick={() => setVars(vars.filter((_, j) => j !== i))}
                        className="mt-1 shrink-0 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                        icon={<Trash2 className="h-4 w-4" />}
                      />
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {/* behaviour */}
        <div>
          <SectionTitle>Behaviour</SectionTitle>
          <Card className="flex flex-col gap-3">
            {!meta.terminal && (
              <CheckboxField
                id="is-start"
                label="Start node (entry point)"
                checked={Boolean(data.isStart)}
                onCheckedChange={(c) => patch({ isStart: c })}
              />
            )}
            <CheckboxField
              id="is-global"
              label="Global (reachable from anywhere)"
              checked={Boolean(data.isGlobal)}
              onCheckedChange={(c) => patch({ isGlobal: c })}
            />
            {Boolean(data.isGlobal) && (
              <TextInput
                name="enter-condition"
                label="Enter condition (Liquid)"
                value={String(data.condition ?? '')}
                onChange={(e) => patch({ condition: e.target.value })}
                placeholder="{{ wants_human == true }}"
                className="font-mono"
              />
            )}
          </Card>
        </div>
      </div>
    );
  };

  // ── edge editing ──
  const renderEdge = () => {
    if (!edge) return null;
    const cond = (edge.data as ConditionEdgeData | undefined)?.condition ?? {
      type: 'ai',
      prompt: '',
    };
    const set = (type: EdgeConditionType, prompt: string) =>
      onChangeEdge(edge.id, { condition: { type, prompt } });
    const isLogic = cond.type === 'logic';

    return (
      <div className="flex flex-col gap-5">
        <Card className="bg-card">
          <div className="font-mono text-xs text-muted-foreground">
            {edge.source} <span className="text-primary">→</span> {edge.target}
          </div>
        </Card>

        <SelectInput
          name="condition-type"
          label="Condition type"
          options={[
            { value: 'ai', label: 'AI — plain language (LLM-evaluated)' },
            { value: 'logic', label: 'Logic — Liquid expression (deterministic)' },
          ]}
          value={cond.type}
          onValueChange={(v) => set(v as EdgeConditionType, cond.prompt)}
        />

        <TextAreaField
          name="condition-prompt"
          label={isLogic ? 'Liquid expression' : 'Condition'}
          rows={4}
          value={cond.prompt}
          onChange={(e) => set(cond.type, e.target.value)}
          placeholder={
            isLogic ? '{{ user_confirmed == true }}' : 'e.g. user said yes (leave blank for always)'
          }
          helperText={
            isLogic
              ? 'Evaluated against extracted variables. No LLM call.'
              : 'The agent decides if this is satisfied. Leave blank to always follow this edge.'
          }
          className={isLogic ? 'font-mono' : undefined}
        />
      </div>
    );
  };

  return (
    <CustomDrawer
      open={open}
      onClose={onClose}
      side="right"
      width="w-[440px] sm:max-w-[440px]"
      title={node ? 'Node settings' : 'Edge settings'}
      footer={
        node ? (
          <div className="flex items-center justify-between">
            <CustomButton
              type="danger"
              size="sm"
              icon={<Trash2 className="h-4 w-4" />}
              onClick={() => onDeleteNode(node.id)}
              disabled={!NODE_REGISTRY[node.type as WorkflowNodeType].deletable}
            >
              Delete
            </CustomButton>
            <CustomButton type="primary" size="sm" onClick={onClose}>
              Done
            </CustomButton>
          </div>
        ) : (
          <div className="flex justify-end">
            <CustomButton type="primary" size="sm" onClick={onClose}>
              Done
            </CustomButton>
          </div>
        )
      }
    >
      {node ? renderNode() : renderEdge()}
    </CustomDrawer>
  );
};

export default NodeConfigDrawer;
