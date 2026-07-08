'use client';

import { Check, Loader2, PhoneIncoming, Search, Sparkles, X } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { CustomButton, CustomModal, SelectInput } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import {
  listChannelPhoneNumbers,
  listTelnyxPhoneNumbers,
  listTwilioPhoneNumbers,
} from '@/services/channelService';
import type { ChannelPhoneNumber } from '@/services/channelService';
import type { AgentPhoneNumberInput } from '@/types/agent';
import type { Channel } from '@/types/integration';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { formatPhoneWithDash, getCountryIso2FromPhone } from '@/utils/phoneUtils';
import * as FlagIcons from 'country-flag-icons/react/3x2';

type FlagKey = keyof typeof FlagIcons;

interface AssignPhoneNumberModalProps {
  open: boolean;
  onClose: () => void;
  channels: Channel[];
  channelsLoading: boolean;
  /** Numbers already attached to this agent in the form state — pre-selected
   * and shown with a "Currently assigned" badge so users can de-select them. */
  currentlyAssigned: AgentPhoneNumberInput[];
  /** Called when the user clicks Assign — the parent reconciles the rows
   * into the form's `phone_numbers` state. */
  onAssign: (rows: AgentPhoneNumberInput[]) => void;
}

type RowStatus = 'assigned' | 'available' | 'in-use';

interface DecoratedRow extends ChannelPhoneNumber {
  status: RowStatus;
}

export default function AssignPhoneNumberModal({
  open,
  onClose,
  channels,
  channelsLoading,
  currentlyAssigned,
  onAssign,
}: AssignPhoneNumberModalProps) {
  const [serviceProvider, setServiceProvider] = useState<string>('');
  const [channelId, setChannelId] = useState<string>('');
  const [numbers, setNumbers] = useState<ChannelPhoneNumber[]>([]);
  const [loadingNumbers, setLoadingNumbers] = useState(false);
  const [search, setSearch] = useState('');
  // Selected numbers across the modal session, keyed by `${channelId}|${number}`
  // so a user can pick across providers/channels in a single open.
  const [selected, setSelected] = useState<Map<string, AgentPhoneNumberInput>>(new Map());

  // ─── reset when reopened ────────────────────────────────────────────────
  useEffect(() => {
    if (!open) return;
    const seed = new Map<string, AgentPhoneNumberInput>();
    currentlyAssigned.forEach((row) => {
      if (row.channel_id && row.number) {
        seed.set(`${row.channel_id}|${row.number}`, { ...row });
      }
    });
    setSelected(seed);
    setSearch('');
    // Default the dropdowns to the first available option for convenience.
    const firstProvider = channels[0]?.channel_type ?? '';
    setServiceProvider(firstProvider);
    setChannelId(channels.find((c) => c.channel_type === firstProvider)?.id ?? '');
  }, [open, channels, currentlyAssigned]);

  // ─── derived options ────────────────────────────────────────────────────
  const serviceProviderOptions = useMemo(() => {
    const seen = new Set<string>();
    const opts: { value: string; label: string }[] = [];
    channels.forEach((c) => {
      if (!seen.has(c.channel_type)) {
        seen.add(c.channel_type);
        opts.push({ value: c.channel_type, label: titleCase(c.channel_type) });
      }
    });
    return opts;
  }, [channels]);

  const channelOptions = useMemo(
    () =>
      channels
        .filter((c) => !serviceProvider || c.channel_type === serviceProvider)
        .map((c) => ({ value: c.id, label: c.name })),
    [channels, serviceProvider],
  );

  // ─── fetch numbers for the selected channel ─────────────────────────────
  useEffect(() => {
    if (!open || !channelId) {
      setNumbers([]);
      return;
    }
    const selectedChannel = channels.find((c) => c.id === channelId);
    const providerType = selectedChannel?.channel_type?.toLowerCase();
    const fetcher =
      providerType === 'twilio'
        ? listTwilioPhoneNumbers
        : providerType === 'telnyx'
          ? listTelnyxPhoneNumbers
          : listChannelPhoneNumbers;
    let cancelled = false;
    setLoadingNumbers(true);
    fetcher(channelId)
      .then((rows) => {
        if (!cancelled) setNumbers(rows);
      })
      .catch((err) => {
        if (!cancelled) handleApiError(err);
      })
      .finally(() => {
        if (!cancelled) setLoadingNumbers(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, channelId, channels]);

  // ─── selection helpers ──────────────────────────────────────────────────
  const keyOf = (chId: string, num: string) => `${chId}|${num}`;

  const toggleNumber = (n: ChannelPhoneNumber) => {
    setSelected((prev) => {
      const next = new Map(prev);
      const k = keyOf(n.channel_id, n.number);
      if (next.has(k)) next.delete(k);
      else
        next.set(k, {
          number: n.number,
          channel_id: n.channel_id,
          label: n.label ?? null,
        });
      return next;
    });
  };

  const handleAssign = () => {
    onAssign(Array.from(selected.values()));
    onClose();
  };

  // ─── derived list: sort + filter + status decoration ────────────────────
  const decoratedRows: DecoratedRow[] = useMemo(() => {
    const q = search.trim().toLowerCase();
    return numbers
      .map<DecoratedRow>((n) => {
        const isCurrentlyAssigned = currentlyAssigned.some(
          (a) => a.channel_id === n.channel_id && a.number === n.number,
        );
        const status: RowStatus = isCurrentlyAssigned
          ? 'assigned'
          : n.assigned_to
            ? 'in-use'
            : 'available';
        return { ...n, status };
      })
      .filter((n) => {
        if (!q) return true;
        const hay = `${n.number} ${n.label ?? ''} ${n.assigned_to?.agent_name ?? ''}`.toLowerCase();
        return hay.includes(q);
      })
      .sort((a, b) => {
        // assigned → available → in-use
        const order = { assigned: 0, available: 1, 'in-use': 2 } as const;
        if (order[a.status] !== order[b.status]) return order[a.status] - order[b.status];
        return a.number.localeCompare(b.number);
      });
  }, [numbers, currentlyAssigned, search]);

  const counts = useMemo(() => {
    let avail = 0;
    let inUse = 0;
    numbers.forEach((n) => {
      const mine = currentlyAssigned.some(
        (a) => a.channel_id === n.channel_id && a.number === n.number,
      );
      if (mine) return;
      if (n.assigned_to) inUse += 1;
      else avail += 1;
    });
    return { total: numbers.length, available: avail, inUse };
  }, [numbers, currentlyAssigned]);

  const selectedCount = selected.size;
  const hasNumbers = numbers.length > 0;
  const showingZero = !loadingNumbers && decoratedRows.length === 0 && hasNumbers;

  const selectAllVisible = () => {
    setSelected((prev) => {
      const next = new Map(prev);
      decoratedRows.forEach((n) => {
        if (n.status === 'in-use') return;
        const k = keyOf(n.channel_id, n.number);
        if (!next.has(k)) {
          next.set(k, { number: n.number, channel_id: n.channel_id, label: n.label ?? null });
        }
      });
      return next;
    });
  };

  const clearSelection = () => setSelected(new Map());

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title="Assign phone numbers"
      hideFooter
      width="sm:max-w-xl"
    >
      <div className="flex flex-col gap-4">
        {/* Provider + channel picker — compact two-column row */}
        <div className="grid gap-3 sm:grid-cols-2">
          <SelectInput
            name="assign_service_provider"
            label="Service provider"
            options={serviceProviderOptions}
            value={serviceProvider}
            onValueChange={(v) => {
              setServiceProvider(v);
              // Auto-jump channel to the first one in this provider so the
              // numbers list refreshes without an extra click.
              const first = channels.find((c) => c.channel_type === v);
              setChannelId(first?.id ?? '');
            }}
            loading={channelsLoading}
            placeholder="Select a provider"
          />
          <SelectInput
            name="assign_channel"
            label="Channel"
            options={channelOptions}
            value={channelId}
            onValueChange={setChannelId}
            loading={channelsLoading}
            disabled={!serviceProvider}
            placeholder={serviceProvider ? 'Select a channel' : 'Pick a provider first'}
          />
        </div>

        {/* Numbers section */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <p className="text-sm font-medium text-foreground">Phone numbers</p>
              {hasNumbers && (
                <div className="flex items-center gap-1">
                  <Badge
                    variant="secondary"
                    className="h-5 px-1.5 text-[10px] font-medium tabular-nums"
                  >
                    {counts.total} total
                  </Badge>
                  {counts.available > 0 && (
                    <Badge className="h-5 border-emerald-500/20 bg-emerald-500/10 px-1.5 text-[10px] font-medium tabular-nums text-emerald-700 hover:bg-emerald-500/10 dark:text-emerald-400">
                      {counts.available} free
                    </Badge>
                  )}
                  {counts.inUse > 0 && (
                    <Badge
                      variant="secondary"
                      className="h-5 px-1.5 text-[10px] font-medium tabular-nums text-muted-foreground"
                    >
                      {counts.inUse} in use
                    </Badge>
                  )}
                </div>
              )}
            </div>
            {selectedCount > 0 && (
              <CustomButton
                type="text"
                onClick={clearSelection}
                className="h-auto px-0 py-0 text-[11px] font-medium text-muted-foreground hover:bg-transparent hover:text-foreground"
              >
                Clear
              </CustomButton>
            )}
          </div>

          {/* Search */}
          {hasNumbers && (
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by number, label, or agent name"
                className={cn(
                  'h-9 w-full rounded-lg border border-border/70 bg-background pl-8 pr-8 text-sm transition-colors',
                  'placeholder:text-muted-foreground/70 focus-visible:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20',
                )}
              />
              {search && (
                <CustomButton
                  type="text"
                  onClick={() => setSearch('')}
                  aria-label="Clear search"
                  className="absolute right-2 top-1/2 flex size-5 -translate-y-1/2 items-center justify-center rounded-md p-0 text-muted-foreground hover:bg-muted hover:text-foreground"
                >
                  <X className="size-3" />
                </CustomButton>
              )}
            </div>
          )}

          {/* List container */}
          <div className="overflow-hidden rounded-xl border border-border/70 bg-card">
            {loadingNumbers ? (
              <SkeletonRows />
            ) : !channelId ? (
              <EmptyState
                icon={<PhoneIncoming className="size-5" />}
                title="Pick a channel"
                description="Choose a channel above to see its phone numbers."
              />
            ) : !hasNumbers ? (
              <EmptyState
                icon={<PhoneIncoming className="size-5" />}
                title="No phone numbers found"
                description="Configure your integration or buy a number in your provider's console first."
              />
            ) : showingZero ? (
              <EmptyState
                icon={<Search className="size-5" />}
                title="No matches"
                description={`Nothing matches "${search.trim()}". Try a shorter query.`}
              />
            ) : (
              <ul
                role="listbox"
                aria-label="Available phone numbers"
                aria-multiselectable
                className="max-h-[320px] divide-y divide-border/50 overflow-y-auto"
              >
                {/* Section header for assigned ones */}
                {decoratedRows[0]?.status === 'assigned' && (
                  <SectionHeader label="Currently assigned" />
                )}
                {decoratedRows.map((n, i) => {
                  const k = keyOf(n.channel_id, n.number);
                  const isSelected = selected.has(k);
                  const taken = n.status === 'in-use';
                  const prev = decoratedRows[i - 1];
                  // Insert section headers when status group changes
                  const showAvailableHeader =
                    n.status === 'available' && (!prev || prev.status !== 'available');
                  const showInUseHeader =
                    n.status === 'in-use' && (!prev || prev.status !== 'in-use');

                  return (
                    <NumberRowGroup
                      key={k}
                      headerForAvailable={showAvailableHeader}
                      headerForInUse={showInUseHeader}
                    >
                      <NumberRow
                        number={n.number}
                        label={n.label ?? null}
                        status={n.status}
                        agentName={n.assigned_to?.agent_name ?? null}
                        isSelected={isSelected}
                        disabled={taken}
                        onToggle={() => !taken && toggleNumber(n)}
                      />
                    </NumberRowGroup>
                  );
                })}
              </ul>
            )}
          </div>

          {/* Bulk actions */}
          {hasNumbers && !loadingNumbers && !showingZero && (
            <div className="flex items-center justify-between gap-2 text-[11px] text-muted-foreground">
              <CustomButton
                type="link"
                onClick={selectAllVisible}
                icon={<Sparkles className="size-3" />}
                className="h-auto gap-1 p-0 text-[11px] font-medium text-primary hover:text-primary/80"
              >
                Select all available
              </CustomButton>
              <span className="tabular-nums">
                Showing {decoratedRows.length} of {numbers.length}
              </span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between gap-2 border-t border-border/60 pt-3">
          <div className="text-xs text-muted-foreground">
            {selectedCount > 0 ? (
              <span className="inline-flex items-center gap-1.5">
                <span className="inline-flex size-5 items-center justify-center rounded-full bg-primary/10 text-[10px] font-semibold text-primary tabular-nums">
                  {selectedCount}
                </span>
                <span>{selectedCount === 1 ? 'number' : 'numbers'} selected</span>
              </span>
            ) : (
              <span>Nothing selected yet</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <CustomButton type="default" onClick={onClose}>
              Cancel
            </CustomButton>
            <CustomButton
              type="primary"
              onClick={handleAssign}
              disabled={selectedCount === 0}
              icon={<PhoneIncoming className="size-4" />}
            >
              Assign{selectedCount > 0 ? ` (${selectedCount})` : ''}
            </CustomButton>
          </div>
        </div>
      </div>
    </CustomModal>
  );
}

// ─── subcomponents ────────────────────────────────────────────────────────

interface NumberRowProps {
  number: string;
  label: string | null;
  status: RowStatus;
  agentName: string | null;
  isSelected: boolean;
  disabled: boolean;
  onToggle: () => void;
}

function NumberRow({
  number,
  label,
  status,
  agentName,
  isSelected,
  disabled,
  onToggle,
}: NumberRowProps) {
  const iso2 = getCountryIso2FromPhone(number);
  const FlagComponent = iso2
    ? (FlagIcons[iso2 as FlagKey] as React.ComponentType<React.SVGProps<SVGSVGElement>> | undefined)
    : undefined;

  return (
    <CustomButton
      type="text"
      role="option"
      aria-selected={isSelected}
      aria-disabled={disabled}
      onClick={onToggle}
      disabled={disabled}
      title={disabled && agentName ? `In use by ${agentName}` : undefined}
      className={cn(
        'group flex h-auto w-full items-center justify-between gap-3 rounded-none px-3 py-2.5 text-left transition-colors',
        disabled
          ? 'cursor-not-allowed opacity-60'
          : 'cursor-pointer hover:bg-muted/60 focus-visible:bg-muted/60',
        isSelected && !disabled && 'bg-primary/[0.04] hover:bg-primary/[0.07]',
      )}
    >
      <div className="flex min-w-0 flex-1 items-center gap-3">
        {/* Checkbox */}
        <span
          className={cn(
            'flex size-[18px] shrink-0 items-center justify-center rounded-[5px] border transition-all',
            isSelected
              ? 'border-primary bg-primary text-primary-foreground shadow-sm'
              : 'border-border bg-background text-transparent group-hover:border-foreground/30',
            disabled && 'opacity-50',
          )}
        >
          <Check className="size-3" strokeWidth={3} />
        </span>

        {/* Flag */}
        {FlagComponent ? (
          <FlagComponent
            className="h-3.5 w-5 shrink-0 rounded-[2px] object-cover shadow-[0_0_0_0.5px_rgba(0,0,0,0.08)]"
            aria-label={iso2 ?? undefined}
          />
        ) : (
          <span className="inline-flex h-3.5 w-5 shrink-0 items-center justify-center rounded-[2px] bg-muted text-[9px] font-medium text-muted-foreground">
            ?
          </span>
        )}

        {/* Number + label */}
        <div className="flex min-w-0 flex-1 flex-col gap-0.5">
          <span className="flex items-center gap-2">
            <span className="truncate text-sm font-semibold tabular-nums text-foreground">
              {formatPhoneWithDash(number)}
            </span>
            {status === 'assigned' && (
              <Badge className="h-4 border-primary/20 bg-primary/10 px-1.5 text-[9px] font-semibold uppercase tracking-wide text-primary hover:bg-primary/10">
                Assigned
              </Badge>
            )}
          </span>
          {(label || (disabled && agentName)) && (
            <span className="truncate text-[11px] text-muted-foreground">
              {label}
              {label && disabled && agentName && ' · '}
              {disabled && agentName && (
                <span className="text-muted-foreground/80">In use by {agentName}</span>
              )}
            </span>
          )}
        </div>
      </div>
    </CustomButton>
  );
}

function NumberRowGroup({
  headerForAvailable,
  headerForInUse,
  children,
}: {
  headerForAvailable: boolean;
  headerForInUse: boolean;
  children: React.ReactNode;
}) {
  return (
    <>
      {headerForAvailable && <SectionHeader label="Available" />}
      {headerForInUse && <SectionHeader label="In use by other agents" muted />}
      <li>{children}</li>
    </>
  );
}

function SectionHeader({ label, muted }: { label: string; muted?: boolean }) {
  return (
    <li
      aria-hidden
      className={cn(
        'sticky top-0 z-[1] flex items-center gap-2 border-b border-border/40 bg-muted/40 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.06em] backdrop-blur-sm',
        muted ? 'text-muted-foreground/70' : 'text-muted-foreground',
      )}
    >
      <span className="h-px flex-1 bg-border/60" />
      <span>{label}</span>
      <span className="h-px flex-1 bg-border/60" />
    </li>
  );
}

function EmptyState({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-10 text-center">
      <span className="flex size-9 items-center justify-center rounded-full bg-muted text-muted-foreground">
        {icon}
      </span>
      <p className="text-sm font-medium text-foreground">{title}</p>
      <p className="max-w-[280px] text-[11px] leading-relaxed text-muted-foreground">
        {description}
      </p>
    </div>
  );
}

function SkeletonRows() {
  return (
    <div className="divide-y divide-border/50">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 px-3 py-2.5">
          <span className="size-[18px] shrink-0 rounded-[5px] bg-muted/70" />
          <span className="h-3.5 w-5 shrink-0 rounded-[2px] bg-muted/70" />
          <div className="flex flex-1 flex-col gap-1.5">
            <span className="h-3 w-32 rounded bg-muted/70" />
            <span className="h-2 w-20 rounded bg-muted/50" />
          </div>
        </div>
      ))}
      <div className="flex items-center justify-center gap-2 px-3 py-3 text-[11px] text-muted-foreground">
        <Loader2 className="size-3 animate-spin" />
        Fetching numbers from provider…
      </div>
    </div>
  );
}

function titleCase(s: string): string {
  return s.toLowerCase().replace(/\b([a-z])/g, (m) => m.toUpperCase());
}
