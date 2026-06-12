'use client';

import React from 'react';
import { Plus, Trash2 } from 'lucide-react';

import { cn } from '@/utils/cn';
import CustomDrawer from '@/components/shared/CustomDrawer';
import CustomButton from '@/components/shared/CustomButton';
import { NODE_REGISTRY } from '@/components/workflows/nodeRegistry';
import type {
  ConditionEdgeData,
  EdgeConditionType,
  WorkflowEdge,
  WorkflowNode,
  WorkflowNodeType,
} from '@/types/workflow';

type D = Record<string, unknown>;

interface Props {
  node: WorkflowNode | null;
  edge: WorkflowEdge | null;
  onClose: () => void;
  onChangeNode: (id: string, data: D) => void;
  onChangeEdge: (id: string, data: ConditionEdgeData) => void;
  onDeleteNode: (id: string) => void;
}

// ── small styled primitives ──────────────────────────────────────────────────
const Label: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="mb-1.5 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
    {children}
  </div>
);

const input =
  'w-full rounded-md border border-border bg-background px-2.5 py-1.5 text-sm outline-none ring-primary/40 placeholder:text-muted-foreground focus:ring-2';

const Section: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="mb-4">{children}</div>
);

const Toggle: React.FC<{ label: string; checked: boolean; onChange: (v: boolean) => void }> = ({
  label,
  checked,
  onChange,
}) => (
  <label className="flex cursor-pointer items-center gap-2 text-sm text-foreground">
    <input
      type="checkbox"
      checked={checked}
      onChange={(e) => onChange(e.target.checked)}
      className="h-4 w-4 accent-primary"
    />
    {label}
  </label>
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

  // ── node editing ──
  const renderNode = () => {
    if (!node) return null;
    const type = node.type as WorkflowNodeType;
    const meta = NODE_REGISTRY[type];
    const Icon = meta.icon;
    const data = node.data as D;
    const patch = (p: D) => onChangeNode(node.id, { ...data, ...p });
    const fm = (data.messagePlan as D | undefined)?.firstMessage ?? '';
    const setFirstMessage = (v: string) =>
      patch({ messagePlan: { ...(data.messagePlan as D), firstMessage: v } });

    const vars = ((data.variableExtractionPlan as D | undefined)?.output as D[] | undefined) ?? [];
    const setVars = (next: D[]) => patch({ variableExtractionPlan: { output: next } });

    return (
      <>
        <div className="mb-4 flex items-center gap-2.5">
          <span
            className={cn(
              'inline-flex h-8 w-8 items-center justify-center rounded-md',
              meta.accent.chip,
            )}
          >
            <Icon className="h-4 w-4" />
          </span>
          <div className="min-w-0 flex-1">
            <div className="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
              {meta.label}
            </div>
            <input
              className="-ml-0.5 w-full rounded bg-transparent px-0.5 text-sm font-semibold outline-none focus:bg-accent"
              value={String(data.name ?? node.id)}
              onChange={(e) => patch({ name: e.target.value })}
            />
          </div>
        </div>

        {type === 'conversation' && (
          <Section>
            <Label>First message (spoken on entry)</Label>
            <textarea
              className={cn(input, 'min-h-[60px] resize-y')}
              value={String(fm)}
              onChange={(e) => setFirstMessage(e.target.value)}
            />
          </Section>
        )}

        {(type === 'conversation' || type === 'decision') && (
          <Section>
            <Label>Prompt</Label>
            <textarea
              className={cn(input, 'min-h-[100px] resize-y')}
              value={String(data.prompt ?? '')}
              onChange={(e) => patch({ prompt: e.target.value })}
              placeholder={
                type === 'decision'
                  ? 'Optional guidance for AI-routed branches'
                  : 'What should the agent do at this step?'
              }
            />
            <p className="mt-1 text-xs text-muted-foreground">
              The LLM (model/temperature) comes from the agent. Use {'{{variables}}'} for dynamic
              values.
            </p>
          </Section>
        )}

        {type === 'conversation' && (
          <Section>
            <div className="mb-1.5 flex items-center justify-between">
              <Label>Extract variables</Label>
              <button
                type="button"
                onClick={() =>
                  setVars([...vars, { title: '', type: 'string', enum: [], description: '' }])
                }
                className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs text-primary hover:bg-accent"
              >
                <Plus className="h-3 w-3" /> Add
              </button>
            </div>
            <div className="flex flex-col gap-2">
              {vars.map((v, i) => (
                <div key={i} className="flex items-center gap-1.5">
                  <input
                    className={cn(input, 'font-mono')}
                    placeholder="variable_name"
                    value={String(v.title ?? '')}
                    onChange={(e) =>
                      setVars(vars.map((x, j) => (j === i ? { ...x, title: e.target.value } : x)))
                    }
                  />
                  <input
                    className={input}
                    placeholder="description"
                    value={String(v.description ?? '')}
                    onChange={(e) =>
                      setVars(
                        vars.map((x, j) => (j === i ? { ...x, description: e.target.value } : x)),
                      )
                    }
                  />
                  <button
                    type="button"
                    onClick={() => setVars(vars.filter((_, j) => j !== i))}
                    className="shrink-0 rounded p-1 text-muted-foreground hover:text-destructive"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
              {vars.length === 0 && (
                <p className="text-xs text-muted-foreground">
                  No variables extracted at this node.
                </p>
              )}
            </div>
          </Section>
        )}

        {type === 'tool' && (
          <Section>
            <Label>Tool</Label>
            <input
              className={cn(input, 'font-mono')}
              placeholder="tool id (webhook / custom / MCP)"
              value={String(data.toolId ?? '')}
              onChange={(e) => patch({ toolId: e.target.value, tool: undefined })}
            />
            <p className="mt-1 text-xs text-muted-foreground">
              Reference an existing Tool. Built-in actions use an inline tool type.
            </p>
          </Section>
        )}

        {type === 'transferCall' && (
          <Section>
            <Label>Destination number</Label>
            <input
              className={cn(input, 'font-mono')}
              placeholder="+15551234567"
              value={String((data.destination as D | undefined)?.number ?? '')}
              onChange={(e) => patch({ destination: { type: 'number', number: e.target.value } })}
            />
            <div className="mt-3" />
            <Label>Message before transfer</Label>
            <textarea
              className={cn(input, 'min-h-[50px] resize-y')}
              value={String(fm)}
              onChange={(e) => setFirstMessage(e.target.value)}
            />
          </Section>
        )}

        {type === 'endCall' && (
          <Section>
            <Label>Goodbye message</Label>
            <textarea
              className={cn(input, 'min-h-[60px] resize-y')}
              value={String(fm)}
              onChange={(e) => setFirstMessage(e.target.value)}
            />
          </Section>
        )}

        <Section>
          <div className="flex flex-col gap-2 rounded-lg border border-border bg-muted/30 p-3">
            {!meta.terminal && (
              <Toggle
                label="Start node (entry point)"
                checked={Boolean(data.isStart)}
                onChange={(v) => patch({ isStart: v })}
              />
            )}
            <Toggle
              label="Global (reachable from anywhere)"
              checked={Boolean(data.isGlobal)}
              onChange={(v) => patch({ isGlobal: v })}
            />
            {Boolean(data.isGlobal) && (
              <div>
                <Label>Enter condition (Liquid)</Label>
                <input
                  className={cn(input, 'font-mono')}
                  placeholder="{{ wants_human == true }}"
                  value={String(data.condition ?? '')}
                  onChange={(e) => patch({ condition: e.target.value })}
                />
              </div>
            )}
          </div>
        </Section>
      </>
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
    return (
      <>
        <div className="mb-4">
          <div className="text-sm font-semibold">Edge condition</div>
          <div className="mt-0.5 font-mono text-xs text-muted-foreground">
            {edge.source} → {edge.target}
          </div>
        </div>
        <Section>
          <Label>Type</Label>
          <div className="inline-flex rounded-lg border border-border p-0.5">
            {(['ai', 'logic'] as EdgeConditionType[]).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => set(t, cond.prompt)}
                className={cn(
                  'rounded-md px-3 py-1 text-sm capitalize transition-colors',
                  cond.type === t
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                {t}
              </button>
            ))}
          </div>
        </Section>
        <Section>
          <Label>
            {cond.type === 'logic' ? 'Liquid expression' : 'Condition (plain language)'}
          </Label>
          <textarea
            className={cn(input, 'min-h-[80px] resize-y', cond.type === 'logic' && 'font-mono')}
            placeholder={
              cond.type === 'logic'
                ? '{{ user_confirmed == true }}'
                : 'e.g. user said yes (leave blank for always)'
            }
            value={cond.prompt}
            onChange={(e) => set(cond.type, e.target.value)}
          />
        </Section>
      </>
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
