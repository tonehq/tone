'use client';

import { motion, useReducedMotion, type Variants } from 'framer-motion';
import { ChevronRight } from 'lucide-react';
import Link from 'next/link';

import { IconChip } from '@/components/shared';
import { SETTINGS_NAV_GROUPS, type SettingsNavItem } from '@/components/settings/navConfig';
import { cn, getInitials } from '@/lib/utils';
import { useAuthStore } from '@/stores/auth';

// The overview lists only the labelled sections (skip the ungrouped Overview
// entry from the shared rail config).
const GROUPS = SETTINGS_NAV_GROUPS.filter((g) => g.heading);

function SettingsRow({ row, variants }: { row: SettingsNavItem; variants: Variants }) {
  const Icon = row.icon;
  return (
    <motion.div variants={variants}>
      <Link
        href={row.href}
        className={cn(
          'group flex items-center gap-4 px-4 py-4 transition-colors sm:px-5',
          'hover:bg-accent/40',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring',
        )}
      >
        <IconChip
          icon={<Icon strokeWidth={1.75} />}
          tone="primary"
          size="lg"
          className="group-hover:from-primary group-hover:via-primary group-hover:to-primary group-hover:text-primary-foreground group-hover:ring-primary"
        />
        <div className="min-w-0 flex-1">
          <p className="text-[14px] font-semibold tracking-tight text-foreground">{row.label}</p>
          <p className="mt-0.5 truncate text-[13px] leading-relaxed text-muted-foreground">
            {row.description}
          </p>
        </div>
        <ChevronRight className="size-4 shrink-0 text-muted-foreground/40 transition-all duration-200 group-hover:translate-x-0.5 group-hover:text-foreground" />
      </Link>
    </motion.div>
  );
}

export default function SettingsOverview() {
  const user = useAuthStore((s) => s.user);
  const reduceMotion = useReducedMotion();
  const firstName = user?.first_name?.trim();
  const initials = getInitials(user?.first_name, user?.last_name) || 'U';

  const container: Variants = {
    hidden: {},
    show: {
      transition: { staggerChildren: reduceMotion ? 0 : 0.04, delayChildren: 0.04 },
    },
  };
  const item: Variants = {
    hidden: { opacity: 0, y: reduceMotion ? 0 : 8 },
    show: { opacity: 1, y: 0, transition: { duration: 0.3, ease: [0.22, 1, 0.36, 1] } },
  };

  return (
    <div className="w-full">
      {/* ── Page header (matches the other settings pages) ──────── */}
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-primary/80">
            <span className="size-1.5 rounded-full bg-primary" />
            Workspace settings
          </div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">Settings</h1>
          <p className="mt-1 max-w-xl text-sm leading-relaxed text-muted-foreground">
            {firstName ? `Welcome back, ${firstName}. ` : ''}
            Manage your account, workspace, and connected services in one place.
          </p>
        </div>
        <Link
          href="/settings/profile"
          className="group hidden items-center gap-2.5 rounded-xl border border-border/70 bg-card px-3 py-2 transition-colors hover:border-primary/30 hover:bg-accent/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background sm:flex"
        >
          <span className="flex size-9 items-center justify-center rounded-full bg-primary/10 text-[12px] font-semibold text-primary ring-1 ring-inset ring-primary/15">
            {initials}
          </span>
          <span className="min-w-0 text-left">
            <span className="block truncate text-[13px] font-medium leading-tight text-foreground">
              {[user?.first_name, user?.last_name].filter(Boolean).join(' ') || 'Your account'}
            </span>
            <span className="block truncate text-[11px] leading-tight text-muted-foreground">
              View profile
            </span>
          </span>
        </Link>
      </div>

      {/* ── Grouped lists ───────────────────────────────────────── */}
      <motion.div variants={container} initial="hidden" animate="show" className="space-y-8">
        {GROUPS.map((group) => (
          <section key={group.heading ?? ''}>
            <div className="mb-3 flex items-baseline justify-between gap-3 px-1">
              <h2 className="text-[12px] font-semibold uppercase tracking-[0.12em] text-foreground/80">
                {group.heading}
              </h2>
              <p className="truncate text-[12px] text-muted-foreground">{group.caption}</p>
            </div>
            <div className="overflow-hidden rounded-2xl border border-border/70 bg-card shadow-sm">
              <div className="divide-y divide-border/60">
                {group.items.map((row) => (
                  <SettingsRow key={row.href} row={row} variants={item} />
                ))}
              </div>
            </div>
          </section>
        ))}
      </motion.div>
    </div>
  );
}
