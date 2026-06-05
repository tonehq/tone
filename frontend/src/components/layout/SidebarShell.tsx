'use client';

import { motion } from 'framer-motion';
import { ChevronsLeft, ChevronsRight } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { CustomButton } from '@/components/shared';
import { Logo, LogoIcon } from '@/components/ui/logo';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/primitives';
import { cn } from '@/lib/utils';

// Shared, presentational sidebar used by BOTH the main app sidebar
// (components/layout/sidebar.tsx) and the settings rail (settings/layout.tsx).
// Only the *content* differs — each consumer passes its own nav data plus a
// `primary` slot (workspace switcher / back-to-app) and a `footer` slot
// (account menu). Everything else — frame, brand, collapse toggles, grouped
// nav, the sliding active indicator, tooltips — lives here so the two can
// never visually drift.

export interface SidebarNavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  // When true, the item is active only on an exact pathname match (used for
  // index routes like `/settings` that would otherwise match every child).
  exact?: boolean;
}

export interface SidebarNavGroup {
  // `null` heading renders no label (and, when collapsed, no divider before it).
  heading: string | null;
  items: SidebarNavItem[];
}

export function isSidebarItemActive(pathname: string, item: SidebarNavItem): boolean {
  if (item.exact) return pathname === item.href;
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}

function SidebarNavLink({
  item,
  active,
  collapsed,
  layoutId,
}: {
  item: SidebarNavItem;
  active: boolean;
  collapsed: boolean;
  layoutId: string;
}) {
  const Icon = item.icon;
  const content = (
    <Link
      href={item.href}
      aria-current={active ? 'page' : undefined}
      aria-label={collapsed ? item.label : undefined}
      className={cn(
        'group relative flex items-center rounded-md text-[13px] font-medium transition-all duration-150',
        active
          ? 'bg-sidebar-accent text-foreground'
          : 'text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground',
        collapsed ? 'mx-auto h-10 w-10 justify-center' : 'gap-2.5 px-2.5 py-[7px]',
      )}
    >
      <Icon
        className={cn(
          'shrink-0 transition-colors',
          collapsed ? 'h-[18px] w-[18px]' : 'h-4 w-4',
          active ? 'text-foreground' : 'text-muted-foreground group-hover:text-foreground',
        )}
      />
      {!collapsed && <span className="truncate">{item.label}</span>}
      {active && !collapsed && (
        <motion.div
          layoutId={layoutId}
          className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-primary"
          transition={{ type: 'spring', stiffness: 500, damping: 35 }}
        />
      )}
      {active && collapsed && (
        <motion.div
          layoutId={`${layoutId}-collapsed`}
          className="absolute -left-[7px] top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-primary"
          transition={{ type: 'spring', stiffness: 500, damping: 35 }}
        />
      )}
    </Link>
  );

  if (collapsed) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>{content}</TooltipTrigger>
        <TooltipContent side="right" sideOffset={12}>
          {item.label}
        </TooltipContent>
      </Tooltip>
    );
  }
  return content;
}

export interface SidebarShellProps {
  groups: SidebarNavGroup[];
  collapsed: boolean;
  onToggle: () => void;
  // Unique prefix so the two sidebars' framer-motion shared-layout animations
  // never collide (e.g. 'app-sidebar' vs 'settings-rail').
  activeLayoutId: string;
  // Slots — the only things that differ between the two sidebars. Each receives
  // the collapsed flag so it can render an icon-only variant.
  primary: (collapsed: boolean) => React.ReactNode;
  footer: (collapsed: boolean) => React.ReactNode;
  brandHref?: string;
  // Positioning differences (e.g. `fixed ...` for the app sidebar,
  // `hidden lg:flex` for the settings rail).
  className?: string;
  expandedWidth?: number;
  collapsedWidth?: number;
}

export function SidebarShell({
  groups,
  collapsed,
  onToggle,
  activeLayoutId,
  primary,
  footer,
  brandHref = '/home',
  className,
  expandedWidth = 240,
  collapsedWidth = 60,
}: SidebarShellProps) {
  const pathname = usePathname();

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? collapsedWidth : expandedWidth }}
      transition={{ duration: 0.2, ease: [0.25, 0.1, 0.25, 1] }}
      className={cn(
        // `shrink-0` keeps the rail at its exact width when it's a flex child
        // (the settings layout) — without it the content column squeezes it
        // narrower than the fixed app sidebar.
        'flex shrink-0 flex-col overflow-hidden border-r border-sidebar-border bg-sidebar',
        className,
      )}
    >
      {/* ── Header ─────────────────────────────────────────────── */}
      <div className="shrink-0 border-b border-sidebar-border">
        {collapsed ? (
          <div className="flex flex-col items-center gap-3 py-3">
            <Tooltip>
              <TooltipTrigger asChild>
                <Link href={brandHref} className="block">
                  <LogoIcon className="h-8 w-8" />
                </Link>
              </TooltipTrigger>
              <TooltipContent side="right" sideOffset={12}>
                Tone
              </TooltipContent>
            </Tooltip>
            {primary(true)}
          </div>
        ) : (
          <>
            <div className="flex h-12 items-center justify-between px-4">
              <Link href={brandHref}>
                <Logo size="sm" />
              </Link>
              <CustomButton
                type="text"
                onClick={onToggle}
                aria-label="Collapse sidebar"
                icon={<ChevronsLeft className="h-4 w-4" />}
                className="size-7 rounded-md p-0 text-muted-foreground hover:bg-foreground/[0.06] hover:text-foreground"
              />
            </div>
            <div className="px-3 pb-3 pt-1">{primary(false)}</div>
          </>
        )}
      </div>

      {collapsed && (
        <div className="flex shrink-0 justify-center pb-1 pt-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <CustomButton
                type="text"
                onClick={onToggle}
                aria-label="Expand sidebar"
                icon={<ChevronsRight className="h-4 w-4" />}
                className="size-8 rounded-lg p-0 text-muted-foreground hover:bg-foreground/[0.06] hover:text-foreground"
              />
            </TooltipTrigger>
            <TooltipContent side="right" sideOffset={12}>
              Expand sidebar
            </TooltipContent>
          </Tooltip>
        </div>
      )}

      {/* ── Nav ────────────────────────────────────────────────── */}
      <nav className={cn('flex-1 overflow-y-auto', collapsed ? 'px-[10px] py-1' : 'px-3 py-2')}>
        {groups.map((group, gIdx) => (
          <div key={group.heading ?? `group-${gIdx}`} className={cn(gIdx > 0 && 'mt-4')}>
            {collapsed
              ? gIdx > 0 && <div className="mx-auto my-1.5 w-6 border-t border-sidebar-border/60" />
              : group.heading && (
                  <p className="mb-1 px-2.5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/50">
                    {group.heading}
                  </p>
                )}
            <div className={cn('space-y-1', collapsed && 'flex flex-col items-center')}>
              {group.items.map((item) => (
                <SidebarNavLink
                  key={item.href}
                  item={item}
                  active={isSidebarItemActive(pathname, item)}
                  collapsed={collapsed}
                  layoutId={activeLayoutId}
                />
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* ── Footer ─────────────────────────────────────────────── */}
      <div
        className={cn(
          'shrink-0 border-t border-sidebar-border',
          collapsed ? 'px-[10px] py-2' : 'px-3 py-2',
        )}
      >
        {footer(collapsed)}
      </div>
    </motion.aside>
  );
}
