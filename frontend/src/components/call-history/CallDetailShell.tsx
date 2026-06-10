'use client';

import { AccountMenu } from '@/components/layout/AccountMenu';
import { isSidebarItemActive, SidebarShell } from '@/components/layout/SidebarShell';
import { CustomButton } from '@/components/shared';
import { useNavigation } from '@/contexts/navigation';
import { getCallLogById } from '@/services/callLogService';
import type { CallLogRow } from '@/types/callLog';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { ArrowLeft, ChevronRight } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';

import { buildCallDetailNav } from './callDetailNav';
import { CallDetailProvider } from './CallDetailContext';

interface CallDetailShellProps {
  callId: string;
  children: React.ReactNode;
}

const CALL_HISTORY_HREF = '/call-history';

const CallDetailShell: React.FC<CallDetailShellProps> = ({ callId, children }) => {
  const router = useRouter();
  const pathname = usePathname();
  const { sidebarCollapsed, toggleSidebar } = useNavigation();

  const [callLog, setCallLog] = useState<CallLogRow | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getCallLogById(callId)
      .then((data) => {
        if (!cancelled) setCallLog(data);
      })
      .catch((error) => {
        if (!cancelled) handleApiError(error);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [callId]);

  const basePath = `${CALL_HISTORY_HREF}/${callId}`;
  const navGroups = useMemo(() => buildCallDetailNav(basePath), [basePath]);
  const flatItems = useMemo(() => navGroups.flatMap((g) => g.items), [navGroups]);

  const agentName = callLog?.agent_name ?? '';
  const crumbLabel = agentName || (loading ? 'Loading…' : 'Detail');

  const detailContextValue = useMemo(() => ({ callLog, loading }), [callLog, loading]);

  return (
    <CallDetailProvider value={detailContextValue}>
      <div className="flex h-full w-full min-w-0 bg-background">
        {/* ── Detail rail (desktop) — shares SidebarShell with the app sidebar ── */}
        <SidebarShell
          groups={navGroups}
          collapsed={sidebarCollapsed}
          onToggle={toggleSidebar}
          activeLayoutId="call-detail-rail"
          className="hidden lg:flex"
          primary={(collapsed) => <BackToCallHistory collapsed={collapsed} />}
          footer={(collapsed) => <AccountMenu collapsed={collapsed} />}
        />

        {/* ── Content column ────────────────────────────────────────── */}
        <div className="flex h-full min-h-0 w-full min-w-0 flex-col">
          {/* Mobile top bar */}
          <div className="flex shrink-0 flex-col gap-2 border-b border-border/60 bg-sidebar/60 px-4 pb-2 pt-2.5 backdrop-blur lg:hidden">
            <div className="flex items-center gap-3">
              <Link
                href={CALL_HISTORY_HREF}
                aria-label="Back to call history"
                className="inline-flex size-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-sidebar-accent/60 hover:text-foreground"
              >
                <ArrowLeft className="size-4" />
              </Link>
              <span className="truncate text-[15px] font-semibold tracking-tight">
                {crumbLabel}
              </span>
            </div>
            <nav
              aria-label="Call sections (mobile)"
              className="-mx-1 flex items-center gap-1 overflow-x-auto px-1 pb-0.5"
            >
              {flatItems.map((item) => {
                const Icon = item.icon;
                const active = isSidebarItemActive(pathname, item);
                return (
                  <CustomButton
                    key={item.href}
                    type="text"
                    size="sm"
                    onClick={() => router.push(item.href)}
                    aria-current={active ? 'page' : undefined}
                    className={cn(
                      'shrink-0 gap-1.5 rounded-full px-3 text-[12px]',
                      active
                        ? 'bg-sidebar-accent text-foreground'
                        : 'text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground',
                    )}
                  >
                    <Icon className="size-3.5" />
                    {item.label}
                  </CustomButton>
                );
              })}
            </nav>
          </div>

          {/* Page header — breadcrumb + section heading */}
          <header className="flex shrink-0 flex-col gap-1.5 border-b border-border/60 px-5 py-4 lg:px-8">
            <nav
              aria-label="Breadcrumb"
              className="flex items-center gap-1.5 text-sm text-muted-foreground"
            >
              <Link href={CALL_HISTORY_HREF} className="transition-colors hover:text-foreground">
                Call History
              </Link>
              <ChevronRight className="size-3.5" aria-hidden />
              <span className="truncate font-medium text-foreground">{crumbLabel}</span>
            </nav>
            <h1 className="text-xl font-semibold tracking-tight text-foreground">
              {agentName || 'Call Details'}
            </h1>
          </header>

          {/* Body — the routed section. `max-w-6xl` matches the header's
              effective width (header is full-bleed within the same padding),
              so the breadcrumb, audio bar, metrics grid and pipeline cards
              all align to the same left/right edges instead of pinching
              narrower than the heading. */}
          <main className="min-h-0 flex-1 overflow-auto px-5 py-5 lg:px-8 lg:py-6">
            <div className="mx-auto h-full max-w-6xl">{children}</div>
          </main>
        </div>
      </div>
    </CallDetailProvider>
  );
};

/** Primary rail slot — return to the call history list. */
function BackToCallHistory({ collapsed }: { collapsed: boolean }) {
  if (collapsed) {
    return (
      <Link
        href={CALL_HISTORY_HREF}
        aria-label="Back to call history"
        className="mx-auto flex size-8 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-inset ring-primary/10 transition-colors hover:bg-primary/15"
      >
        <ArrowLeft className="h-4 w-4 text-primary" strokeWidth={1.75} />
      </Link>
    );
  }

  return (
    <Link
      href={CALL_HISTORY_HREF}
      className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left transition-colors hover:bg-sidebar-accent/60"
    >
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-inset ring-primary/10">
        <ArrowLeft className="h-[18px] w-[18px] text-primary" strokeWidth={1.75} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-[14px] font-semibold leading-tight tracking-tight">
          Call History
        </p>
        <p className="mt-0.5 truncate text-[11.5px] leading-tight text-muted-foreground">
          Back to call history
        </p>
      </div>
    </Link>
  );
}

export default CallDetailShell;
