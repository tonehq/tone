'use client';

import { BookOpen, Boxes, Wrench } from 'lucide-react';
import { useState } from 'react';

import { useAgentEditor } from '@/components/agents/AgentEditorContext';
import { AgentTypeBadge } from '@/components/agents/AgentTypeBadge';
import { IconChip } from '@/components/shared';
import type { IconChipTone } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { cn } from '@/utils/cn';

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
  tone,
}: {
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  label: string;
  value: number;
  tone: IconChipTone;
}) {
  return (
    <div className="group/stat flex items-center gap-3 rounded-xl border border-border/60 bg-muted/20 px-3 py-2.5 transition-colors duration-300 hover:border-border hover:bg-muted/40">
      <IconChip icon={<Icon strokeWidth={1.75} />} tone={tone} size="lg" interactive />
      <div className="min-w-0">
        <p className="text-[17px] font-semibold leading-none tabular-nums tracking-tight">
          {value}
        </p>
        <p className="mt-1 truncate text-[11px] text-muted-foreground">{label}</p>
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
  const webChannels = detail.web_channels ?? [];
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
          <AgentTypeBadge agentType={detail.agent_type} size="sm" />
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
        {webChannels.length > 0 ? (
          <DetailRow label="Web channels">
            <div className="flex flex-wrap gap-1.5">
              {webChannels.map((c) => (
                <Badge key={c.id} variant="secondary" className="capitalize">
                  {c.channel_type}
                </Badge>
              ))}
            </div>
          </DetailRow>
        ) : null}
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
          <CountStat icon={Wrench} tone="indigo" label="Tools" value={detail.tools?.length ?? 0} />
          <CountStat
            icon={Boxes}
            tone="violet"
            label="MCP servers"
            value={detail.mcp_servers?.length ?? 0}
          />
          <CountStat
            icon={BookOpen}
            tone="sky"
            label="Knowledge docs"
            value={detail.documents?.length ?? 0}
          />
        </div>
      </div>
    </div>
  );
}
