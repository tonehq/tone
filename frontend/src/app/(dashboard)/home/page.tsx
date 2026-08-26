'use client';

import dashboardAtom, { fetchDashboardStatsAtom } from '@/atoms/DashboardAtom';
import { IconChip } from '@/components/shared';
import type { IconChipTone } from '@/components/shared';
import { Card } from '@/components/ui/card';
import { cn } from '@/utils/cn';
import { useAtomValue, useSetAtom } from 'jotai';
import {
  Activity,
  ArrowUpRight,
  Bot,
  CheckCircle2,
  Clock,
  Plus,
  Settings,
  Users,
} from 'lucide-react';
import Link from 'next/link';
import { useEffect } from 'react';

/* ── Stat card config ────────────────────────────────────────────────────── */

interface StatCardConfig {
  label: string;
  key: 'total_agents' | 'active_calls' | 'minutes_used' | 'success_rate';
  suffix: string;
  subtitle: string;
  icon: typeof Bot;
  tone: IconChipTone;
  accent: string;
}

const statCards: StatCardConfig[] = [
  {
    label: 'Total Agents',
    key: 'total_agents',
    suffix: '',
    subtitle: 'All agents',
    icon: Bot,
    tone: 'violet',
    accent: 'from-violet-500/10 via-transparent to-transparent',
  },
  {
    label: 'Active Calls',
    key: 'active_calls',
    suffix: '',
    subtitle: 'Real-time',
    icon: Activity,
    tone: 'emerald',
    accent: 'from-emerald-500/10 via-transparent to-transparent',
  },
  {
    label: 'Minutes Used',
    key: 'minutes_used',
    suffix: '',
    subtitle: 'This month',
    icon: Clock,
    tone: 'sky',
    accent: 'from-sky-500/10 via-transparent to-transparent',
  },
  {
    label: 'Success Rate',
    key: 'success_rate',
    suffix: '%',
    subtitle: 'Last 30 days',
    icon: CheckCircle2,
    tone: 'amber',
    accent: 'from-amber-500/10 via-transparent to-transparent',
  },
];

interface QuickLinkConfig {
  title: string;
  description: string;
  icon: typeof Bot;
  href: string;
  tone: IconChipTone;
  hoverRing: string;
}

const quickLinks: QuickLinkConfig[] = [
  {
    title: 'Agents',
    description: 'Create and manage your AI voice agents',
    icon: Bot,
    href: '/agents',
    tone: 'violet',
    hoverRing: 'group-hover:ring-violet-500/20',
  },
  {
    title: 'Team Members',
    description: 'Manage your team and invite new members',
    icon: Users,
    href: '/settings/members',
    tone: 'rose',
    hoverRing: 'group-hover:ring-pink-500/20',
  },
  {
    title: 'Integrations',
    description: 'Connect services and manage API credentials',
    icon: Settings,
    href: '/settings/integrations',
    tone: 'slate',
    hoverRing: 'group-hover:ring-slate-500/20',
  },
];

/* ── Page ──────────────────────────────────────────────────────────────────── */

export default function HomePage() {
  const { stats, loading } = useAtomValue(dashboardAtom);
  const fetchStats = useSetAtom(fetchDashboardStatsAtom);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  return (
    <div className="animate-page space-y-8">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-1.5">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Welcome to Tone</h1>
          <p className="text-sm text-muted-foreground">
            Build and deploy AI voice agents in minutes. Get started with the quick links below.
          </p>
        </div>

        <Link
          href="/agents"
          className="inline-flex items-center gap-1.5 self-start rounded-lg bg-primary px-3.5 py-2 text-[13px] font-medium text-primary-foreground no-underline shadow-sm transition-all hover:bg-primary/90 hover:shadow sm:self-auto"
        >
          <Plus size={15} />
          Create Agent
        </Link>
      </div>

      {/* ── Stat Cards ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((card) => (
          <Card
            key={card.label}
            className="group relative gap-0 overflow-hidden border-border/60 py-0 transition-all duration-200 hover:-translate-y-0.5 hover:border-border hover:shadow-md"
          >
            <div
              className={cn(
                'pointer-events-none absolute inset-0 bg-gradient-to-br opacity-60 transition-opacity duration-200 group-hover:opacity-100',
                card.accent,
              )}
            />

            <div className="relative flex items-start justify-between px-5 pt-5">
              <IconChip
                icon={<card.icon strokeWidth={1.75} />}
                tone={card.tone}
                size="lg"
                className="transition-transform duration-300 group-hover:scale-[1.04]"
              />
              <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground/80">
                {card.subtitle}
              </span>
            </div>

            <div className="relative px-5 pt-4 pb-5">
              <p className="text-[13px] font-medium text-muted-foreground">{card.label}</p>
              {loading ? (
                <div
                  className="mt-2 h-8 w-16 animate-pulse rounded-md bg-muted"
                  role="status"
                  aria-label={`Loading ${card.label}`}
                />
              ) : (
                <p className="mt-1 text-3xl font-semibold tracking-tight tabular-nums text-foreground">
                  {stats ? `${stats[card.key]}${card.suffix}` : '—'}
                </p>
              )}
            </div>
          </Card>
        ))}
      </div>

      {/* ── Quick Links ─────────────────────────────────────────────────── */}
      <div className="space-y-4">
        <div className="flex items-end justify-between">
          <div>
            <h2 className="text-base font-semibold text-foreground">Quick Links</h2>
            <p className="text-xs text-muted-foreground">Jump to the most-used parts of Tone.</p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {quickLinks.map((link) => (
            <Link key={link.title} href={link.href} className="group block no-underline">
              <Card
                className={cn(
                  'h-full gap-0 border-border/60 py-0 ring-1 ring-transparent transition-all duration-200 hover:-translate-y-0.5 hover:border-border hover:shadow-md',
                  link.hoverRing,
                )}
              >
                <div className="flex h-full flex-col p-5">
                  <div className="mb-4 flex items-start justify-between">
                    <IconChip
                      icon={<link.icon strokeWidth={1.75} />}
                      tone={link.tone}
                      size="lg"
                      className="transition-transform duration-300 group-hover:scale-[1.04]"
                    />
                    <ArrowUpRight
                      size={16}
                      className="text-muted-foreground/40 transition-all duration-200 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-foreground"
                    />
                  </div>

                  <h3 className="text-[15px] font-semibold text-foreground">{link.title}</h3>
                  <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">
                    {link.description}
                  </p>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
