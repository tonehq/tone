'use client';

import dashboardAtom, { fetchDashboardStatsAtom } from '@/atoms/DashboardAtom';
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
  iconBg: string;
  iconColor: string;
  accent: string;
}

const statCards: StatCardConfig[] = [
  {
    label: 'Total Agents',
    key: 'total_agents',
    suffix: '',
    subtitle: 'All agents',
    icon: Bot,
    iconBg: 'bg-violet-500/10',
    iconColor: 'text-violet-600 dark:text-violet-400',
    accent: 'from-violet-500/10 via-transparent to-transparent',
  },
  {
    label: 'Active Calls',
    key: 'active_calls',
    suffix: '',
    subtitle: 'Real-time',
    icon: Activity,
    iconBg: 'bg-emerald-500/10',
    iconColor: 'text-emerald-600 dark:text-emerald-400',
    accent: 'from-emerald-500/10 via-transparent to-transparent',
  },
  {
    label: 'Minutes Used',
    key: 'minutes_used',
    suffix: '',
    subtitle: 'This month',
    icon: Clock,
    iconBg: 'bg-sky-500/10',
    iconColor: 'text-sky-600 dark:text-sky-400',
    accent: 'from-sky-500/10 via-transparent to-transparent',
  },
  {
    label: 'Success Rate',
    key: 'success_rate',
    suffix: '%',
    subtitle: 'Last 30 days',
    icon: CheckCircle2,
    iconBg: 'bg-amber-500/10',
    iconColor: 'text-amber-600 dark:text-amber-400',
    accent: 'from-amber-500/10 via-transparent to-transparent',
  },
];

interface QuickLinkConfig {
  title: string;
  description: string;
  icon: typeof Bot;
  href: string;
  iconBg: string;
  iconColor: string;
  hoverRing: string;
}

const quickLinks: QuickLinkConfig[] = [
  {
    title: 'Agents',
    description: 'Create and manage your AI voice agents',
    icon: Bot,
    href: '/agents',
    iconBg: 'bg-violet-500/10',
    iconColor: 'text-violet-600 dark:text-violet-400',
    hoverRing: 'group-hover:ring-violet-500/20',
  },
  {
    title: 'Team Members',
    description: 'Manage your team and invite new members',
    icon: Users,
    href: '/members',
    iconBg: 'bg-pink-500/10',
    iconColor: 'text-pink-600 dark:text-pink-400',
    hoverRing: 'group-hover:ring-pink-500/20',
  },
  {
    title: 'Integrations',
    description: 'Connect services and manage API credentials',
    icon: Settings,
    href: '/integrations',
    iconBg: 'bg-slate-500/10',
    iconColor: 'text-slate-600 dark:text-slate-300',
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
        {statCards.map((card) => {
          const value = loading || !stats ? '—' : `${stats[card.key]}${card.suffix}`;

          return (
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
                <div
                  className={cn(
                    'flex size-10 items-center justify-center rounded-xl ring-1 ring-inset ring-border/40',
                    card.iconBg,
                  )}
                >
                  <card.icon size={18} className={card.iconColor} strokeWidth={2.25} />
                </div>
                <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground/80">
                  {card.subtitle}
                </span>
              </div>

              <div className="relative px-5 pt-4 pb-5">
                <p className="text-[13px] font-medium text-muted-foreground">{card.label}</p>
                <p className="mt-1 text-3xl font-semibold tracking-tight tabular-nums text-foreground">
                  {value}
                </p>
              </div>
            </Card>
          );
        })}
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
                    <div
                      className={cn(
                        'flex size-11 items-center justify-center rounded-xl ring-1 ring-inset ring-border/40 transition-transform group-hover:scale-[1.04]',
                        link.iconBg,
                      )}
                    >
                      <link.icon size={20} className={link.iconColor} strokeWidth={2.25} />
                    </div>
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
