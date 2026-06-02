'use client';

import { CircleAlert, CircleCheck, Pencil } from 'lucide-react';
import { useFormContext, useWatch } from 'react-hook-form';

import { CustomButton } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import type { AgentFormState } from '@/types/agent';
import { cn } from '@/utils/cn';

interface ReviewStepProps {
  onJump: (stepIndex: number) => void;
}

interface RowSpec {
  label: string;
  value: React.ReactNode;
  /** Determines whether the row contributes to the card's "configured" score
   * and whether it gets hidden when empty. */
  hideWhenEmpty?: boolean;
}

function isMissing(value: React.ReactNode): boolean {
  if (value == null || value === '' || value === '—') return true;
  if (typeof value === 'string' && value.trim() === '') return true;
  return false;
}

function Card({
  title,
  stepIndex,
  onJump,
  rows,
}: {
  title: string;
  stepIndex: number;
  onJump: (i: number) => void;
  rows: RowSpec[];
}) {
  const total = rows.length;
  const filled = rows.filter((r) => !isMissing(r.value)).length;
  const allDone = filled === total;
  const noneDone = filled === 0;

  // Hide-when-empty rows that are empty get dropped from the visible list.
  // Rows without that flag always render (e.g. counts that legitimately
  // show "0 selected").
  const visibleRows = rows.filter((r) => !r.hideWhenEmpty || !isMissing(r.value));

  return (
    <section className="rounded-xl border border-border/70 bg-card px-4 py-3">
      <header className="mb-2 flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <h3 className="font-display text-sm font-semibold tracking-tight text-foreground">
            {title}
          </h3>
          <span
            className={cn(
              'inline-flex shrink-0 items-center gap-1 rounded-full px-1.5 text-[10px] font-medium',
              allDone
                ? 'bg-emerald-500/15 text-emerald-700 dark:bg-emerald-500/25 dark:text-emerald-200'
                : noneDone
                  ? 'bg-muted text-muted-foreground'
                  : 'bg-amber-500/15 text-amber-700 dark:bg-amber-500/25 dark:text-amber-200',
            )}
          >
            {allDone ? <CircleCheck className="size-3" /> : <CircleAlert className="size-3" />}
            {allDone ? 'Ready' : noneDone ? 'Not set' : `${filled}/${total}`}
          </span>
        </div>
        <CustomButton
          type="text"
          size="sm"
          icon={<Pencil className="size-3" />}
          onClick={() => onJump(stepIndex)}
          className="h-6 px-1.5 text-[11px] text-muted-foreground hover:text-foreground"
        >
          Edit
        </CustomButton>
      </header>
      {visibleRows.length === 0 ? (
        <p className="text-[12px] text-muted-foreground">Nothing set yet — click Edit to add.</p>
      ) : (
        <dl className="flex flex-col gap-1 text-sm text-foreground">
          {visibleRows.map((r) => (
            <Row key={r.label} label={r.label} value={r.value} />
          ))}
        </dl>
      )}
    </section>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[120px_1fr] items-baseline gap-3">
      <dt className="text-[11px] text-muted-foreground">{label}</dt>
      <dd className="min-w-0 text-[13px] text-foreground">
        {isMissing(value) ? <span className="text-muted-foreground">—</span> : value}
      </dd>
    </div>
  );
}

export default function ReviewStep({ onJump }: ReviewStepProps) {
  const { control } = useFormContext<AgentFormState>();
  const state = useWatch({ control }) as AgentFormState;

  const cards: { title: string; stepIndex: number; rows: RowSpec[] }[] = [
    {
      title: 'Basics',
      stepIndex: 0,
      rows: [
        { label: 'Name', value: state.name, hideWhenEmpty: true },
        { label: 'Description', value: state.description, hideWhenEmpty: true },
        {
          label: 'Direction',
          value: state.agent_type ? (
            <Badge variant="secondary" className="capitalize">
              {state.agent_type}
            </Badge>
          ) : null,
        },
        {
          label: 'Active',
          value: (
            <span className="inline-flex items-center gap-1.5">
              <span
                className={cn(
                  'size-1.5 rounded-full',
                  state.is_active ? 'bg-emerald-500' : 'bg-muted-foreground/40',
                )}
              />
              {state.is_active ? 'Yes' : 'No'}
            </span>
          ),
        },
        { label: 'First message', value: state.config?.first_message, hideWhenEmpty: true },
        {
          label: 'End call message',
          value: state.config?.end_call_message,
          hideWhenEmpty: true,
        },
      ],
    },
    {
      title: 'Prompt',
      stepIndex: 1,
      rows: [
        {
          label: 'System prompt',
          value: state.config?.system_prompt_template ? (
            <span className="line-clamp-3 whitespace-pre-wrap text-[13px]">
              {state.config.system_prompt_template}
            </span>
          ) : null,
          hideWhenEmpty: true,
        },
      ],
    },
    {
      title: 'AI',
      stepIndex: 2,
      rows: [
        {
          label: 'LLM provider',
          value: (state.config?.llm_settings as { provider_id?: string } | undefined)?.provider_id,
          hideWhenEmpty: true,
        },
        {
          label: 'LLM model',
          value: (state.config?.llm_settings as { model_id?: string } | undefined)?.model_id,
          hideWhenEmpty: true,
        },
        {
          label: 'KB embedding model',
          value: state.config?.knowledge_model_id,
          hideWhenEmpty: true,
        },
        {
          label: 'Temperature',
          value: state.config?.llm_settings?.temperature,
          hideWhenEmpty: true,
        },
        {
          label: 'Max completion tokens',
          value: state.config?.llm_settings?.max_completion_tokens,
          hideWhenEmpty: true,
        },
        {
          label: 'History tokens',
          value: state.config?.conversation_history_token_limit,
          hideWhenEmpty: true,
        },
      ],
    },
    {
      title: 'Voice',
      stepIndex: 3,
      rows: [
        { label: 'Language', value: state.config?.voice_settings?.language, hideWhenEmpty: true },
        {
          label: 'TTS provider',
          value: state.config?.voice_settings?.provider_id,
          hideWhenEmpty: true,
        },
        {
          label: 'TTS model',
          value: (state.config?.voice_settings as { model_id?: string } | undefined)?.model_id,
          hideWhenEmpty: true,
        },
        { label: 'Voice', value: state.config?.voice_settings?.voice_id, hideWhenEmpty: true },
        { label: 'Speed', value: state.config?.voice_settings?.speed, hideWhenEmpty: true },
        {
          label: 'STT provider',
          value: (state.config?.stt_settings as { provider_id?: string } | undefined)?.provider_id,
          hideWhenEmpty: true,
        },
        { label: 'STT model', value: state.config?.stt_settings?.model, hideWhenEmpty: true },
      ],
    },
    {
      title: 'Tools & MCP',
      stepIndex: 4,
      rows: [
        { label: 'Tools', value: `${state.tool_ids?.length ?? 0} selected` },
        { label: 'MCP servers', value: `${state.mcp_server_ids?.length ?? 0} attached` },
      ],
    },
    {
      title: 'Knowledge & Phone',
      stepIndex: 5,
      rows: [
        { label: 'Documents', value: `${state.upload_ids?.length ?? 0} attached` },
        { label: 'Phone numbers', value: `${state.phone_numbers?.length ?? 0} assigned` },
      ],
    },
  ];

  const totalRows = cards.reduce((sum, c) => sum + c.rows.length, 0);
  const filledRows = cards.reduce(
    (sum, c) => sum + c.rows.filter((r) => !isMissing(r.value)).length,
    0,
  );
  const pct = totalRows === 0 ? 0 : Math.round((filledRows / totalRows) * 100);

  return (
    <div className="flex flex-col gap-3">
      {/* Compact progress strip */}
      <div className="flex items-center gap-3 rounded-xl border border-border/70 bg-card px-4 py-2">
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Setup
          </span>
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
            <div
              className={cn(
                'h-full rounded-full transition-all',
                pct >= 90
                  ? 'bg-emerald-500'
                  : pct >= 50
                    ? 'bg-amber-500'
                    : 'bg-muted-foreground/50',
              )}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
        <span className="shrink-0 text-[11px] font-medium tabular-nums text-muted-foreground">
          {filledRows}/{totalRows} fields · {pct}%
        </span>
      </div>

      {cards.map((c) => (
        <Card key={c.title} title={c.title} stepIndex={c.stepIndex} onJump={onJump} rows={c.rows} />
      ))}
    </div>
  );
}
