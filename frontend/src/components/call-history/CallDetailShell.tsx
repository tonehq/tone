'use client';

import { AccountMenu, AccountMenuSettingsLink } from '@/components/layout/AccountMenu';
import { isSidebarItemActive, SidebarShell } from '@/components/layout/SidebarShell';
import { CustomButton, CustomTooltip } from '@/components/shared';
import { useNavigation } from '@/contexts/navigation';
import { getCallLogById } from '@/services/callLogService';
import type { CallLogRow } from '@/types/callLog';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { ArrowLeft, Check, ChevronRight, Copy } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { buildCallDetailNav } from './callDetailNav';
import { CallDetailProvider } from './CallDetailContext';
import CallSummaryCard from './CallSummaryCard';

interface CallDetailShellProps {
  callId: string;
  children: React.ReactNode;
}

const CALL_HISTORY_HREF = '/call-history';

/** Only honor an in-app absolute path as the back target — guards against an
 * open-redirect via a crafted `?from=` (external or protocol-relative URL). */
function safeBackHref(from: string | null): string {
  // Reject backslashes: browsers normalize `\` to `/`, so `/\evil.com` would
  // resolve to the protocol-relative `//evil.com` and pass the `//` check.
  if (from && from.startsWith('/') && !from.startsWith('//') && !from.includes('\\')) return from;
  return CALL_HISTORY_HREF;
}

const CallDetailShell: React.FC<CallDetailShellProps> = ({ callId, children }) => {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { sidebarCollapsed, toggleSidebar } = useNavigation();

  // Where "back" returns to. When the call was opened from an agent's Call
  // History tab the row-click carries `?from=<agent path>`, so back stays in
  // the agent editor instead of bouncing to the global list. Defaults to the
  // global call history when absent/untrusted.
  const backHref = safeBackHref(searchParams.get('from'));
  const navSearch = backHref === CALL_HISTORY_HREF ? '' : `?from=${encodeURIComponent(backHref)}`;

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
  const navGroups = useMemo(() => buildCallDetailNav(basePath, navSearch), [basePath, navSearch]);
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
          primary={(collapsed) => <BackToCallHistory collapsed={collapsed} href={backHref} />}
          footer={(collapsed) => (
            <AccountMenu collapsed={collapsed}>
              <AccountMenuSettingsLink />
            </AccountMenu>
          )}
        />

        {/* ── Content column ────────────────────────────────────────── */}
        <div className="flex h-full min-h-0 w-full min-w-0 flex-col">
          {/* Mobile top bar */}
          <div className="flex shrink-0 flex-col gap-2 border-b border-border/60 bg-sidebar/60 px-4 pb-2 pt-2.5 backdrop-blur lg:hidden">
            <div className="flex items-center gap-3">
              <Link
                href={backHref}
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

          {/* Page header — breadcrumb + section heading. Inner wrapper uses
              the same `max-w-6xl mx-auto` constraint as the summary card and
              body below, so all three regions share the exact same content
              edges on wide displays. */}
          <header className="shrink-0 border-b border-border/60 bg-muted px-5 py-4 lg:px-8">
            <div className="mx-auto flex w-full max-w-6xl flex-col gap-1.5">
              <nav
                aria-label="Breadcrumb"
                className="flex items-center gap-1.5 text-sm text-muted-foreground"
              >
                <Link href={backHref} className="transition-colors hover:text-foreground">
                  Call History
                </Link>
                <ChevronRight className="size-3.5" aria-hidden />
                <span className="truncate font-medium text-foreground">{crumbLabel}</span>
              </nav>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex min-w-0 flex-wrap items-center gap-2">
                  <h1 className="truncate text-xl font-semibold tracking-tight text-foreground">
                    {agentName || 'Call Details'}
                  </h1>
                  <CallIdPill callId={callId} />
                </div>
                <CopyLinkButton />
              </div>
            </div>
          </header>

          {/* Persistent call-summary card — pinned above every tab body.
              Lives outside `<main>` so the badges + Call Details stay
              visible while the tab content scrolls below. Rendered only
              once the call has loaded to avoid a layout flash. */}
          {callLog && <CallSummaryCard callLog={callLog} />}

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

/** Primary rail slot — return to wherever the user opened the call from
 * (the global list by default, or the agent's Call History tab when scoped). */
function BackToCallHistory({ collapsed, href }: { collapsed: boolean; href: string }) {
  if (collapsed) {
    return (
      <Link
        href={href}
        aria-label="Back to call history"
        className="mx-auto flex size-8 items-center justify-center rounded-lg bg-primary/10 ring-1 ring-inset ring-primary/10 transition-colors hover:bg-primary/15"
      >
        <ArrowLeft className="h-4 w-4 text-primary" strokeWidth={1.75} />
      </Link>
    );
  }

  return (
    <Link
      href={href}
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

/** Truncate a UUID-style id to `xxxxxxxx…xxxx` for compact display. */
function truncateCallId(id: string): string {
  if (id.length <= 14) return id;
  return `${id.slice(0, 8)}…${id.slice(-4)}`;
}

/**
 * Small monospace pill rendered next to the title — shows a truncated call id
 * with the full id available via tooltip.
 */
function CallIdPill({ callId }: { callId: string }) {
  return (
    <CustomTooltip content={callId}>
      <span className="inline-flex shrink-0 items-center rounded-md bg-muted/60 px-2 py-0.5 font-mono text-[11px] text-muted-foreground">
        {truncateCallId(callId)}
      </span>
    </CustomTooltip>
  );
}

/**
 * Top-right action — copies the current page URL to the clipboard and
 * surfaces a transient "Copied" state for ~1.5s. Silently no-ops if the
 * clipboard API is unavailable (e.g. insecure context).
 */
function CopyLinkButton() {
  const [copied, setCopied] = useState(false);
  // Track the reset timer so we can (a) clear it on unmount to avoid a late
  // setState on a stale component, and (b) cancel a stale timer if the user
  // clicks Copy again before the prior one fires.
  const resetTimerRef = useRef<number | null>(null);

  useEffect(
    () => () => {
      if (resetTimerRef.current != null) window.clearTimeout(resetTimerRef.current);
    },
    [],
  );

  const onCopy = useCallback(async () => {
    if (typeof window === 'undefined') return;
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      if (resetTimerRef.current != null) window.clearTimeout(resetTimerRef.current);
      resetTimerRef.current = window.setTimeout(() => {
        setCopied(false);
        resetTimerRef.current = null;
      }, 1500);
    } catch {
      // Clipboard write can fail in insecure contexts — fail silently.
    }
  }, []);

  return (
    <CustomTooltip content={copied ? 'Copied' : 'Copy page link'}>
      <CustomButton
        type="default"
        size="xs"
        icon={
          copied ? (
            <Check className="size-3 text-emerald-600 dark:text-emerald-400" />
          ) : (
            <Copy className="size-3" />
          )
        }
        onClick={onCopy}
        aria-label="Copy page link"
      >
        {copied ? 'Copied' : 'Copy link'}
      </CustomButton>
    </CustomTooltip>
  );
}

export default CallDetailShell;
