'use client';

import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/utils/cn';
import {
  Activity,
  ArrowUpRight,
  BarChart3,
  Bot,
  CheckCircle2,
  Clock,
  Phone,
  Plus,
  Settings,
  TrendingUp,
  Users,
  Zap,
} from 'lucide-react';
import Link from 'next/link';

/* ── Data ─────────────────────────────────────────────────────────────────── */

const stats = [
  {
    label: 'Total Agents',
    value: '6',
    change: '+2 this week',
    trend: 'up' as const,
    icon: Bot,
    accent: 'from-primary/20 to-primary/5',
    accentBorder: 'border-t-primary',
    iconColor: 'text-primary',
  },
  {
    label: 'Active Calls',
    value: '0',
    change: 'Real-time',
    trend: 'neutral' as const,
    icon: Activity,
    accent: 'from-emerald-500/20 to-emerald-500/5',
    accentBorder: 'border-t-emerald-500',
    iconColor: 'text-emerald-500',
  },
  {
    label: 'Minutes Used',
    value: '0',
    change: 'This month',
    trend: 'neutral' as const,
    icon: Clock,
    accent: 'from-blue-500/20 to-blue-500/5',
    accentBorder: 'border-t-blue-500',
    iconColor: 'text-blue-500',
  },
  {
    label: 'Success Rate',
    value: '0%',
    change: 'Last 30 days',
    trend: 'neutral' as const,
    icon: CheckCircle2,
    accent: 'from-amber-500/20 to-amber-500/5',
    accentBorder: 'border-t-amber-500',
    iconColor: 'text-amber-500',
  },
];

const quickActions = [
  {
    label: 'Create Agent',
    href: '/agents',
    icon: Plus,
    color: 'bg-primary text-primary-foreground hover:bg-primary/90',
  },
];

const quickLinks = [
  {
    title: 'Agents',
    description: 'Create and manage your AI voice agents',
    icon: Bot,
    href: '/agents',
    iconBg: 'bg-primary/10',
    iconColor: 'text-primary',
  },
  {
    title: 'Phone Numbers',
    description: 'Manage your phone numbers for calls',
    icon: Phone,
    href: '/phone-numbers',
    iconBg: 'bg-emerald-500/10',
    iconColor: 'text-emerald-500',
  },
  {
    title: 'Analytics',
    description: 'View performance metrics and insights',
    icon: BarChart3,
    href: '/analytics',
    iconBg: 'bg-blue-500/10',
    iconColor: 'text-blue-500',
  },
  {
    title: 'Actions',
    description: 'Configure automated actions and triggers',
    icon: Zap,
    href: '/actions',
    iconBg: 'bg-amber-500/10',
    iconColor: 'text-amber-500',
  },
  {
    title: 'Team Members',
    description: 'Manage your team and invite new members',
    icon: Users,
    href: '/settings',
    iconBg: 'bg-pink-500/10',
    iconColor: 'text-pink-500',
  },
  {
    title: 'Settings',
    description: 'Configure your organization settings',
    icon: Settings,
    href: '/settings',
    iconBg: 'bg-muted',
    iconColor: 'text-muted-foreground',
  },
];

/* ── Page ──────────────────────────────────────────────────────────────────── */

export default function HomePage() {
  return (
    <div className="animate-page space-y-8 p-6 lg:p-8">
      {/* ── Header + Quick Actions ──────────────────────────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Welcome to Tone</h1>
          <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">
            Build and deploy AI voice agents in minutes. Get started with the quick links below.
          </p>
        </div>

        <div className="flex gap-2">
          {quickActions.map((action) => (
            <Link
              key={action.label}
              href={action.href}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-[13px] font-medium no-underline transition-colors',
                action.color,
              )}
            >
              <action.icon size={15} />
              {action.label}
            </Link>
          ))}
        </div>
      </div>

      {/* ── Stat Cards ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card
            key={stat.label}
            className={cn(
              'group relative overflow-hidden border-t-2 py-0 transition-all hover:shadow-md',
              stat.accentBorder,
            )}
          >
            {/* Subtle gradient background */}
            <div
              className={cn(
                'pointer-events-none absolute inset-0 bg-gradient-to-br opacity-0 transition-opacity group-hover:opacity-100',
                stat.accent,
              )}
            />

            <CardContent className="relative px-5 py-4">
              <div className="mb-3 flex items-center justify-between">
                <span className="text-[13px] font-medium text-muted-foreground">{stat.label}</span>
                <div
                  className={cn(
                    'flex size-9 items-center justify-center rounded-lg bg-muted/50',
                    stat.iconColor,
                  )}
                >
                  <stat.icon size={18} />
                </div>
              </div>

              <div className="text-3xl font-bold tracking-tight text-foreground">{stat.value}</div>

              <div className="mt-1.5 flex items-center gap-1">
                {stat.trend === 'up' && <TrendingUp size={12} className="text-emerald-500" />}
                <span
                  className={cn(
                    'text-xs',
                    stat.trend === 'up' ? 'text-emerald-600' : 'text-muted-foreground',
                  )}
                >
                  {stat.change}
                </span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* ── Quick Links ─────────────────────────────────────────────────── */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-foreground">Quick Links</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {quickLinks.map((link) => (
            <Link key={link.title} href={link.href} className="group no-underline">
              <Card className="h-full gap-0 py-0 transition-all group-hover:-translate-y-0.5 group-hover:shadow-md">
                <CardContent className="p-5">
                  <div className="mb-3 flex items-center gap-3">
                    <div
                      className={cn(
                        'flex size-10 items-center justify-center rounded-xl transition-transform group-hover:scale-105',
                        link.iconBg,
                      )}
                    >
                      <link.icon size={20} className={link.iconColor} />
                    </div>

                    <span className="flex-1 text-[15px] font-semibold text-foreground">
                      {link.title}
                    </span>

                    <ArrowUpRight
                      size={16}
                      className="text-muted-foreground/50 transition-all group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-muted-foreground"
                    />
                  </div>

                  <p className="text-[13px] leading-relaxed text-muted-foreground">
                    {link.description}
                  </p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
