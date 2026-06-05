'use client';

import { BookOpen, Boxes, Phone, Wrench } from 'lucide-react';
import { useState } from 'react';

import { useAgentEditor } from '@/components/agents/AgentEditorContext';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import type { AgentDirection } from '@/types/agent';
import { cn } from '@/utils/cn';

const DIRECTION_STYLES: Record<AgentDirection, string> = {
  inbound:
    'bg-emerald-500/15 text-emerald-700 ring-1 ring-inset ring-emerald-500/20 dark:bg-emerald-500/25 dark:text-emerald-200 dark:ring-emerald-400/40',
  outbound:
    'bg-violet-500/15 text-violet-700 ring-1 ring-inset ring-violet-500/20 dark:bg-violet-500/25 dark:text-violet-200 dark:ring-violet-400/40',
  both: 'bg-sky-500/15 text-sky-700 ring-1 ring-inset ring-sky-500/20 dark:bg-sky-500/25 dark:text-sky-200 dark:ring-sky-400/40',
};

function DetailRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted-foreground/70">
        {label}
      </p>
      <div className="mt-1 text-[13px] text-foreground">{children}</div>
    </div>
  );
}

function CountStat({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  label: string;
  value: number;
}) {
  return (
    <div className="flex items-center gap-2.5 rounded-xl border border-border/60 bg-muted/20 px-3 py-2.5">
      <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary ring-1 ring-inset ring-primary/15">
        <Icon className="size-4" strokeWidth={2} />
      </span>
      <div className="min-w-0">
        <p className="text-[15px] font-semibold leading-none tabular-nums">{value}</p>
        <p className="mt-0.5 truncate text-[11px] text-muted-foreground">{label}</p>
      </div>
    </div>
  );
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
  } catch {
    return iso;
  }
}

export default function AgentOverview() {
  const { detail, setActive } = useAgentEditor();
  const [pending, setPending] = useState(false);

  if (!detail) {
    return (
      <div className="rounded-2xl border border-border/70 bg-card p-8 text-center text-sm text-muted-foreground">
        Overview is unavailable for this agent.
      </div>
    );
  }

  const isActive = detail.is_active;
  const language = detail.config?.voice_settings?.language ?? null;
  const phoneNumbers = detail.phone_numbers ?? [];
  const dash = <span className="text-muted-foreground/60">—</span>;

  const handleToggle = async (next: boolean) => {
    setPending(true);
    try {
      await setActive(next);
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="overflow-hidden rounded-2xl border border-border/70 bg-card shadow-sm">
      {/* ── Header ─────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 px-5 py-4">
        <div className="flex min-w-0 items-center gap-2.5">
          <h2 className="truncate text-[17px] font-semibold tracking-tight text-foreground">
            {detail.name}
          </h2>
          <Badge
            className={cn(
              'inline-flex shrink-0 items-center gap-1 px-1.5 py-0 text-[10px] capitalize',
              DIRECTION_STYLES[detail.agent_type],
            )}
          >
            <Phone className="size-2.5" />
            {detail.agent_type}
          </Badge>
        </div>
        <div className="flex items-center gap-2.5">
          <span
            className={cn(
              'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.08em] ring-1 ring-inset',
              isActive
                ? 'bg-emerald-500/10 text-emerald-700 ring-emerald-500/20 dark:text-emerald-300'
                : 'bg-muted text-muted-foreground ring-border',
            )}
          >
            <span
              className={cn(
                'size-1.5 rounded-full',
                isActive ? 'bg-emerald-500' : 'bg-muted-foreground/50',
              )}
            />
            {isActive ? 'Active' : 'Inactive'}
          </span>
          <Switch
            checked={isActive}
            disabled={pending}
            onCheckedChange={handleToggle}
            aria-label={isActive ? 'Deactivate agent' : 'Activate agent'}
          />
        </div>
      </div>

      {/* ── Status & configuration ─────────────────────────────── */}
      <div className="grid grid-cols-1 gap-x-6 gap-y-5 px-5 py-5 sm:grid-cols-2">
        <DetailRow label="LLM model">{detail.llm_model || dash}</DetailRow>
        <DetailRow label="Language">{language || dash}</DetailRow>
        <DetailRow label="Phone numbers">
          {phoneNumbers.length > 0 ? (
            <div className="flex flex-col gap-0.5">
              {phoneNumbers.map((p) => (
                <span key={p.id} className="truncate font-mono text-[12.5px]">
                  {p.number}
                  {p.label ? (
                    <span className="ml-1.5 text-muted-foreground">· {p.label}</span>
                  ) : null}
                </span>
              ))}
            </div>
          ) : (
            <span className="text-muted-foreground">None assigned</span>
          )}
        </DetailRow>
        <DetailRow label="Created">{formatDate(detail.created_at)}</DetailRow>
        {detail.description ? (
          <div className="sm:col-span-2">
            <DetailRow label="Description">{detail.description}</DetailRow>
          </div>
        ) : null}
      </div>

      {/* ── Resources ──────────────────────────────────────────── */}
      <div className="border-t border-border/60 px-5 py-5">
        <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.1em] text-muted-foreground/70">
          Resources
        </p>
        <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-3">
          <CountStat icon={Wrench} label="Tools" value={detail.tools?.length ?? 0} />
          <CountStat icon={Boxes} label="MCP servers" value={detail.mcp_servers?.length ?? 0} />
          <CountStat icon={BookOpen} label="Knowledge docs" value={detail.documents?.length ?? 0} />
        </div>
      </div>
    </div>
  );
}
