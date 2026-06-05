'use client';

import { motion } from 'framer-motion';
import { ArrowLeft, ChevronDown, ChevronsLeft, ChevronsRight, LogOut } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { AvatarBadge } from '@/components/layout/AvatarBadge';
import { ThemeToggleRow } from '@/components/layout/ThemeToggleRow';
import {
  isSettingsItemActive,
  SETTINGS_NAV_GROUPS,
  SETTINGS_NAV_ITEMS,
  type SettingsNavItem,
} from '@/components/settings/navConfig';
import { CustomButton } from '@/components/shared';
import { Logo, LogoIcon } from '@/components/ui/logo';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
  Separator,
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/primitives';
import { cn, getInitials } from '@/lib/utils';
import { useAuthStore } from '@/stores/auth';

const COLLAPSE_KEY = 'settings-rail-collapsed';

function NavLink({
  item,
  active,
  collapsed,
}: {
  item: SettingsNavItem;
  active: boolean;
  collapsed: boolean;
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
          layoutId="settings-active"
          className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-primary"
          transition={{ type: 'spring', stiffness: 500, damping: 35 }}
        />
      )}
      {active && collapsed && (
        <motion.div
          layoutId="settings-active-collapsed"
          className="absolute -left-[5px] top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-primary"
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

function UserFooter({ collapsed }: { collapsed: boolean }) {
  const router = useRouter();
  const { user, clearAuth } = useAuthStore();

  const handleLogout = () => {
    clearAuth();
    router.replace('/login');
  };

  return (
    <Popover>
      <PopoverTrigger asChild>
        {collapsed ? (
          <CustomButton
            type="text"
            aria-label="Account menu"
            className="mx-auto size-10 rounded-lg p-0 hover:bg-sidebar-accent/60"
          >
            <AvatarBadge size="md">{getInitials(user?.first_name, user?.last_name)}</AvatarBadge>
          </CustomButton>
        ) : (
          <CustomButton
            type="text"
            fullWidth
            className="h-auto justify-start gap-2.5 rounded-lg px-2 py-1.5 text-left font-normal hover:bg-sidebar-accent/60"
          >
            <AvatarBadge size="sm">{getInitials(user?.first_name, user?.last_name)}</AvatarBadge>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-[13px] font-medium leading-tight">
                {user?.first_name || user?.email || 'Account'}
              </span>
            </span>
            <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          </CustomButton>
        )}
      </PopoverTrigger>
      <PopoverContent
        side={collapsed ? 'right' : 'top'}
        align="start"
        sideOffset={10}
        className="w-60 p-0"
      >
        <div className="px-4 py-3">
          <p className="text-sm font-semibold">
            {user?.first_name} {user?.last_name}
          </p>
          <p className="mt-0.5 truncate text-xs text-muted-foreground">{user?.email}</p>
        </div>
        <Separator />
        <div className="space-y-0.5 p-1.5">
          <ThemeToggleRow />
        </div>
        <Separator />
        <div className="p-1.5">
          <CustomButton
            type="text"
            fullWidth
            onClick={handleLogout}
            icon={<LogOut className="h-4 w-4" />}
            className="h-9 justify-start gap-3 px-3 font-normal text-destructive hover:bg-destructive/10 hover:text-destructive"
          >
            Log out
          </CustomButton>
        </div>
      </PopoverContent>
    </Popover>
  );
}

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  // Persist rail state across visits (client-only to avoid hydration mismatch).
  useEffect(() => {
    if (typeof window === 'undefined') return;
    setCollapsed(window.localStorage.getItem(COLLAPSE_KEY) === 'true');
  }, []);

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(COLLAPSE_KEY, String(next));
      }
      return next;
    });
  };

  // The Model Providers detail editor is a focused, full-width page with its own
  // back navigation — render it without any settings chrome.
  if (pathname.startsWith('/settings/model-providers/')) {
    return <div className="h-full w-full overflow-y-auto">{children}</div>;
  }

  return (
    <div className="flex h-full w-full min-w-0 bg-background">
      {/* ── Settings rail (desktop) — mirrors the main app sidebar ──── */}
      <motion.aside
        initial={false}
        animate={{ width: collapsed ? 60 : 240 }}
        transition={{ duration: 0.2, ease: [0.25, 0.1, 0.25, 1] }}
        className="hidden shrink-0 flex-col overflow-hidden border-r border-sidebar-border bg-sidebar lg:flex"
      >
        {/* Header */}
        <div className="shrink-0 border-b border-sidebar-border">
          {collapsed ? (
            <div className="flex flex-col items-center gap-3 py-3">
              <Tooltip>
                <TooltipTrigger asChild>
                  <Link href="/home" className="block">
                    <LogoIcon className="h-8 w-8" />
                  </Link>
                </TooltipTrigger>
                <TooltipContent side="right" sideOffset={12}>
                  Tone
                </TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Link
                    href="/home"
                    aria-label="Back to app"
                    className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-primary/10 transition-colors hover:bg-primary/15"
                  >
                    <ArrowLeft className="h-4 w-4 text-primary" strokeWidth={1.75} />
                  </Link>
                </TooltipTrigger>
                <TooltipContent side="right" sideOffset={12}>
                  Back to app
                </TooltipContent>
              </Tooltip>
            </div>
          ) : (
            <>
              <div className="flex h-12 items-center justify-between px-4">
                <Link href="/home">
                  <Logo size="sm" />
                </Link>
                <CustomButton
                  type="text"
                  onClick={toggleCollapsed}
                  aria-label="Collapse sidebar"
                  icon={<ChevronsLeft className="h-4 w-4" />}
                  className="size-7 rounded-md p-0 text-muted-foreground hover:bg-foreground/[0.06] hover:text-foreground"
                />
              </div>
              <div className="px-3 pb-3 pt-1">
                <Link
                  href="/home"
                  className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left transition-colors hover:bg-sidebar-accent/60"
                >
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-primary/10">
                    <ArrowLeft className="h-[18px] w-[18px] text-primary" strokeWidth={1.75} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[14px] font-semibold leading-tight tracking-tight">
                      Settings
                    </p>
                    <p className="mt-0.5 truncate text-[11.5px] leading-tight text-muted-foreground">
                      Back to app
                    </p>
                  </div>
                </Link>
              </div>
            </>
          )}
        </div>

        {collapsed && (
          <div className="flex shrink-0 justify-center pb-1 pt-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <CustomButton
                  type="text"
                  onClick={toggleCollapsed}
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

        <nav className={cn('flex-1 overflow-y-auto', collapsed ? 'px-[10px] py-1' : 'px-3 py-2')}>
          {SETTINGS_NAV_GROUPS.map((group, gIdx) => (
            <div key={group.heading ?? 'top'} className={cn(gIdx > 0 && 'mt-4')}>
              {collapsed
                ? gIdx > 0 && (
                    <div className="mx-auto my-1.5 w-6 border-t border-sidebar-border/60" />
                  )
                : group.heading && (
                    <p className="mb-1 px-2.5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/50">
                      {group.heading}
                    </p>
                  )}
              <div className={cn('space-y-1', collapsed && 'flex flex-col items-center')}>
                {group.items.map((item) => (
                  <NavLink
                    key={item.href}
                    item={item}
                    active={isSettingsItemActive(pathname, item)}
                    collapsed={collapsed}
                  />
                ))}
              </div>
            </div>
          ))}
        </nav>

        <div
          className={cn(
            'shrink-0 border-t border-sidebar-border',
            collapsed ? 'px-[10px] py-2' : 'px-3 py-2',
          )}
        >
          <UserFooter collapsed={collapsed} />
        </div>
      </motion.aside>

      {/* ── Content column ────────────────────────────────────────── */}
      <div className="flex h-full min-h-0 w-full min-w-0 flex-col">
        {/* Mobile top bar */}
        <div className="flex shrink-0 flex-col gap-2 border-b border-border/60 bg-sidebar/60 px-4 pb-2 pt-2.5 backdrop-blur lg:hidden">
          <div className="flex items-center gap-3">
            <Link
              href="/home"
              aria-label="Back to app"
              className="inline-flex size-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-sidebar-accent/60 hover:text-foreground"
            >
              <ArrowLeft className="size-4" />
            </Link>
            <span className="text-[15px] font-semibold tracking-tight">Settings</span>
          </div>
          <nav
            aria-label="Settings sections (mobile)"
            className="-mx-1 flex items-center gap-1 overflow-x-auto px-1 pb-0.5"
          >
            {SETTINGS_NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const active = isSettingsItemActive(pathname, item);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? 'page' : undefined}
                  className={cn(
                    'inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-[12px] font-medium transition-colors',
                    active
                      ? 'bg-sidebar-accent text-foreground'
                      : 'text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground',
                  )}
                >
                  <Icon className="size-3.5" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">{children}</div>
      </div>
    </div>
  );
}
