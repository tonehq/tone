'use client';

import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { AccountMenu } from '@/components/layout/AccountMenu';
import { SidebarShell, isSidebarItemActive } from '@/components/layout/SidebarShell';
import { SETTINGS_NAV_GROUPS, SETTINGS_NAV_ITEMS } from '@/components/settings/navConfig';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/primitives';
import { useNavigation } from '@/contexts/navigation';
import { cn } from '@/lib/utils';

/** Primary slot — return to the main app. */
function BackToApp({ collapsed }: { collapsed: boolean }) {
  if (collapsed) {
    return (
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
    );
  }

  return (
    <Link
      href="/home"
      className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left transition-colors hover:bg-sidebar-accent/60"
    >
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-primary/10">
        <ArrowLeft className="h-[18px] w-[18px] text-primary" strokeWidth={1.75} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-[14px] font-semibold leading-tight tracking-tight">Settings</p>
        <p className="mt-0.5 truncate text-[11.5px] leading-tight text-muted-foreground">
          Back to app
        </p>
      </div>
    </Link>
  );
}

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  // Share the collapse state (and therefore width) with the main app sidebar so
  // switching between the app and settings never changes the rail width.
  const { sidebarCollapsed, toggleSidebar } = useNavigation();

  // The Model Providers detail editor is a focused, full-width page with its own
  // back navigation — render it without any settings chrome.
  if (pathname.startsWith('/settings/model-providers/')) {
    return <div className="h-full w-full overflow-y-auto">{children}</div>;
  }

  return (
    <div className="flex h-full w-full min-w-0 bg-background">
      {/* ── Settings rail (desktop) — shares SidebarShell with the app sidebar ── */}
      <SidebarShell
        groups={SETTINGS_NAV_GROUPS}
        collapsed={sidebarCollapsed}
        onToggle={toggleSidebar}
        activeLayoutId="settings-rail"
        className="hidden lg:flex"
        primary={(c) => <BackToApp collapsed={c} />}
        footer={(c) => <AccountMenu collapsed={c} />}
      />

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
              const active = isSidebarItemActive(pathname, item);
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
