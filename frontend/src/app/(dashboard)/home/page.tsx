'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { useAtomValue, useSetAtom } from 'jotai';
import { motion } from 'framer-motion';
import { Activity, ArrowUpRight, Bot, Cable, CheckCircle2, Clock, Plus, Users } from 'lucide-react';

import dashboardAtom, { fetchDashboardStatsAtom } from '@/atoms/DashboardAtom';
import { PageHeader } from '@/components/layout/page-header';
import { CustomButton } from '@/components/shared';
import { useAuthStore } from '@/stores/auth';
import { cn } from '@/utils/cn';

/* ── config ──────────────────────────────────────────────────────────────── */

interface StatConfig {
  index: string;
  label: string;
  key: 'total_agents' | 'active_calls' | 'minutes_used' | 'success_rate';
  suffix: string;
  subtitle: string;
  icon: typeof Bot;
  live?: boolean;
}

const STATS: StatConfig[] = [
  {
    index: 'S1',
    label: 'Total agents',
    key: 'total_agents',
    suffix: '',
    subtitle: 'All agents',
    icon: Bot,
  },
  {
    index: 'S2',
    label: 'Active calls',
    key: 'active_calls',
    suffix: '',
    subtitle: 'Real-time',
    icon: Activity,
    live: true,
  },
  {
    index: 'S3',
    label: 'Minutes used',
    key: 'minutes_used',
    suffix: '',
    subtitle: 'This month',
    icon: Clock,
  },
  {
    index: 'S4',
    label: 'Success rate',
    key: 'success_rate',
    suffix: '%',
    subtitle: 'Last 30 days',
    icon: CheckCircle2,
  },
];

interface LinkConfig {
  index: string;
  title: string;
  description: string;
  icon: typeof Bot;
  href: string;
}

const QUICK_LINKS: LinkConfig[] = [
  {
    index: '01',
    title: 'Agents',
    description: 'Create and manage your AI voice agents.',
    icon: Bot,
    href: '/agents',
  },
  {
    index: '02',
    title: 'Team members',
    description: 'Invite teammates and manage roles.',
    icon: Users,
    href: '/members',
  },
  {
    index: '03',
    title: 'Integrations',
    description: 'Connect services and API credentials.',
    icon: Cable,
    href: '/integrations',
  },
];

const stagger = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.06, delayChildren: 0.1 } },
};
const item = {
  hidden: { opacity: 0, y: 14 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] as const } },
};

/* ── page ────────────────────────────────────────────────────────────────── */

export default function HomePage() {
  const { stats, loading } = useAtomValue(dashboardAtom);
  const fetchStats = useSetAtom(fetchDashboardStatsAtom);
  const firstName = useAuthStore((s) => s.user?.first_name);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  return (
    <div className="space-y-10">
      <PageHeader
        index="01"
        kicker="Overview"
        title={firstName ? `Welcome back, ${firstName}.` : 'Welcome to Tone.'}
        description="Build and deploy AI voice agents in minutes. Here's where things stand."
        actions={
          <Link href="/agents">
            <CustomButton type="primary" className="group h-10 text-[13px]">
              <Plus className="h-4 w-4" />
              Create agent
            </CustomButton>
          </Link>
        }
      />

      {/* ── stats ─────────────────────────────────────────────────────────── */}
      <motion.div
        className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
        variants={stagger}
        initial="hidden"
        animate="visible"
      >
        {STATS.map((stat) => {
          const value = loading || !stats ? '—' : `${stats[stat.key]}${stat.suffix}`;
          const isLive = stat.live && !loading && !!stats && Number(stats[stat.key]) > 0;
          return (
            <motion.div
              key={stat.key}
              variants={item}
              className="group relative overflow-hidden rounded-xl border border-border bg-card p-5"
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                  {stat.label}
                </span>
                <span className="font-mono text-[10px] tracking-widest text-muted-foreground/40">
                  {stat.index}
                </span>
              </div>

              <div className="mt-5 flex items-end justify-between">
                <span
                  className="text-[2.6rem] font-semibold leading-none tracking-tight tabular-nums text-foreground"
                  style={{ fontFamily: 'var(--font-display)' }}
                >
                  {value}
                </span>
                <stat.icon className="h-5 w-5 text-muted-foreground/35" strokeWidth={1.75} />
              </div>

              <div className="mt-3 flex items-center gap-1.5 text-[12px] text-muted-foreground">
                {isLive && (
                  <span className="relative flex h-1.5 w-1.5">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400/70" />
                    <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-amber-400" />
                  </span>
                )}
                <span>{stat.subtitle}</span>
              </div>

              {/* hairline accent that wipes in on hover */}
              <span className="absolute bottom-0 left-0 h-[2px] w-full origin-left scale-x-0 bg-primary transition-transform duration-500 ease-out group-hover:scale-x-100" />
            </motion.div>
          );
        })}
      </motion.div>

      {/* ── quick links ───────────────────────────────────────────────────── */}
      <div className="space-y-4">
        <div className="flex items-center gap-3 font-mono text-[11px] uppercase tracking-[0.3em] text-muted-foreground">
          <span className="text-primary">02</span>
          <span className="h-px w-8 bg-border" />
          <span>Jump back in</span>
        </div>

        <motion.div
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
          variants={stagger}
          initial="hidden"
          animate="visible"
        >
          {QUICK_LINKS.map((link) => (
            <motion.div key={link.href} variants={item}>
              <Link href={link.href} className="group block no-underline">
                <div
                  className={cn(
                    'relative h-full overflow-hidden rounded-xl border border-border bg-card p-5',
                    'transition-all duration-200 hover:-translate-y-0.5 hover:border-foreground/20',
                  )}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-background transition-colors group-hover:border-primary/40">
                      <link.icon className="h-5 w-5 text-foreground" strokeWidth={1.75} />
                    </div>
                    <ArrowUpRight className="h-4 w-4 text-muted-foreground/40 transition-all duration-200 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-primary" />
                  </div>

                  <div className="mt-4 flex items-center gap-2">
                    <h3 className="text-[15px] font-semibold tracking-tight text-foreground">
                      {link.title}
                    </h3>
                    <span className="font-mono text-[10px] tracking-widest text-muted-foreground/40">
                      {link.index}
                    </span>
                  </div>
                  <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">
                    {link.description}
                  </p>
                </div>
              </Link>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </div>
  );
}
