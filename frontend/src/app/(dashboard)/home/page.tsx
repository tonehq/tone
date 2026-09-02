'use client';

import { fetchPaginatedAgentList, paginatedAgentsAtom } from '@/atoms/AgentsAtom';
import dashboardAtom, { fetchDashboardStatsAtom } from '@/atoms/DashboardAtom';
import { BrandWaveform, CustomButton } from '@/components/shared';
import { useAuthStore } from '@/stores/auth';
import type { AgentListItem } from '@/types/agent';
import { cn } from '@/utils/cn';
import { formatDisplayName } from '@/utils/displayName';
import { useAtomValue, useSetAtom } from 'jotai';
import { ArrowRight, Bot, Plug, Plus, Users } from 'lucide-react';
import Link from 'next/link';
import { useEffect } from 'react';

const AGENT_PREVIEW_COUNT = 5;

interface QuickLinkConfig {
  title: string;
  href: string;
  icon: typeof Bot;
}

const QUICK_LINKS: QuickLinkConfig[] = [
  { title: 'Agents', href: '/agents', icon: Bot },
  { title: 'Team members', href: '/settings/members', icon: Users },
  { title: 'Integrations', href: '/settings/integrations', icon: Plug },
];

function StatRow({ label, value, loading }: { label: string; value: string; loading: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-3">
      <span className="text-caption text-muted-foreground">{label}</span>
      {loading ? (
        <span className="h-4 w-10 animate-pulse rounded bg-muted" />
      ) : (
        <span className="font-display text-heading font-semibold tabular-nums text-foreground">
          {value}
        </span>
      )}
    </div>
  );
}

function AgentRow({ agent }: { agent: AgentListItem }) {
  return (
    <Link
      href={`/agents/edit?id=${agent.uuid}`}
      className="group flex items-center gap-4 py-3 no-underline"
    >
      <span
        className={cn(
          'size-1.5 shrink-0 rounded-full',
          agent.is_active ? 'bg-success' : 'bg-muted-foreground/40',
        )}
      />
      <span className="min-w-0 flex-1 truncate text-body font-medium text-foreground transition-colors group-hover:text-primary">
        {agent.name}
      </span>
      <span className="shrink-0 font-mono text-eyebrow uppercase tracking-[0.16em] text-muted-foreground">
        {agent.agent_type}
      </span>
    </Link>
  );
}

export default function HomePage() {
  const { stats, loading } = useAtomValue(dashboardAtom);
  const fetchStats = useSetAtom(fetchDashboardStatsAtom);
  const { items: agents, loading: agentsLoading } = useAtomValue(paginatedAgentsAtom);
  const fetchAgents = useSetAtom(fetchPaginatedAgentList);
  const user = useAuthStore((s) => s.user);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  useEffect(() => {
    fetchAgents({ page: 1, page_size: AGENT_PREVIEW_COUNT }).catch(() => undefined);
  }, [fetchAgents]);

  const name = formatDisplayName(user?.first_name, user?.last_name, user?.email);
  const preview = agents.slice(0, AGENT_PREVIEW_COUNT);

  return (
    <div className="animate-page mx-auto w-full max-w-6xl space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h1 className="font-display text-[clamp(2rem,3.4vw,2.75rem)] font-semibold leading-none tracking-[-0.04em] text-foreground">
          Overview
        </h1>
        <Link href="/agents" className="no-underline">
          <CustomButton type="primary" icon={<Plus size={15} />} className="h-10">
            Create agent
          </CustomButton>
        </Link>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
        <section className="relative flex h-[16.5rem] flex-col justify-between overflow-hidden rounded-2xl bg-brand-field p-7">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 grid grid-cols-6 opacity-[0.14]"
          >
            <span className="border-r border-white" />
            <span className="border-r border-white" />
            <span className="border-r border-white" />
            <span className="border-r border-white" />
            <span className="border-r border-white" />
          </div>

          <div className="relative z-10">
            <p className="font-mono text-eyebrow uppercase tracking-[0.34em] text-white/50">
              Workspace
            </p>
            <h2 className="mt-4 max-w-md font-display text-[clamp(1.625rem,2.6vw,2.25rem)] font-semibold leading-[1.05] tracking-[-0.035em] text-white">
              {name ? `Welcome back, ${name}.` : 'Welcome back.'}
            </h2>
            <p className="mt-3 max-w-sm text-caption leading-relaxed text-white/60">
              Build, deploy and monitor voice agents on your own stack.
            </p>
          </div>

          <BrandWaveform className="relative z-10 h-14 w-full" />
        </section>

        <section className="flex h-[16.5rem] flex-col rounded-2xl border border-border bg-card p-6 shadow-sm">
          <p className="text-eyebrow uppercase text-muted-foreground">Minutes used</p>
          {loading ? (
            <div
              className="mt-3 h-9 w-24 animate-pulse rounded bg-muted"
              role="status"
              aria-label="Loading minutes used"
            />
          ) : (
            <p className="mt-2 font-display text-[2.25rem] font-semibold leading-none tracking-[-0.04em] tabular-nums text-foreground">
              {stats ? stats.minutes_used : '—'}
            </p>
          )}
          <p className="mt-1.5 text-micro text-muted-foreground/70">This month</p>

          <div className="mt-auto divide-y divide-border border-t border-border">
            <StatRow
              label="Total agents"
              value={stats ? String(stats.total_agents) : '—'}
              loading={loading}
            />
            <StatRow
              label="Active calls"
              value={stats ? String(stats.active_calls) : '—'}
              loading={loading}
            />
            <StatRow
              label="Success rate"
              value={stats ? `${stats.success_rate}%` : '—'}
              loading={loading}
            />
          </div>
        </section>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
        <section className="flex flex-col rounded-2xl border border-border bg-card p-6 shadow-sm">
          <div className="flex items-baseline justify-between gap-4">
            <p className="text-eyebrow uppercase text-muted-foreground">Your agents</p>
            <Link
              href="/agents"
              className="text-caption font-medium text-primary no-underline transition-colors hover:text-primary/80"
            >
              View all
            </Link>
          </div>

          <div className="mt-3 divide-y divide-border border-t border-border">
            {agentsLoading && preview.length === 0 ? (
              Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="flex items-center gap-4 py-3">
                  <span className="size-1.5 shrink-0 rounded-full bg-muted" />
                  <span className="h-4 flex-1 animate-pulse rounded bg-muted" />
                </div>
              ))
            ) : preview.length === 0 ? (
              <div className="py-8 text-center">
                <p className="text-body text-muted-foreground">No agents yet.</p>
                <Link
                  href="/agents"
                  className="mt-1 inline-block text-caption font-medium text-primary no-underline hover:underline"
                >
                  Create your first agent
                </Link>
              </div>
            ) : (
              preview.map((agent) => <AgentRow key={agent.uuid} agent={agent} />)
            )}
          </div>
        </section>

        <section className="flex flex-col rounded-2xl border border-border bg-card p-6 shadow-sm">
          <p className="text-eyebrow uppercase text-muted-foreground">Jump to</p>
          <div className="mt-3 divide-y divide-border border-t border-border">
            {QUICK_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="group flex items-center gap-3 py-3.5 no-underline"
              >
                <link.icon
                  className="size-4 shrink-0 text-muted-foreground transition-colors group-hover:text-foreground"
                  strokeWidth={1.75}
                />
                <span className="min-w-0 flex-1 truncate text-body font-medium text-foreground">
                  {link.title}
                </span>
                <ArrowRight className="size-4 shrink-0 text-muted-foreground/40 transition-all duration-200 group-hover:translate-x-0.5 group-hover:text-foreground" />
              </Link>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
