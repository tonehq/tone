'use client';

import { Check, Loader2, PhoneIncoming } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { CustomButton, CustomModal, SelectInput } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import { listChannelPhoneNumbers } from '@/services/channelService';
import type { ChannelPhoneNumber } from '@/services/channelService';
import type { AgentPhoneNumberInput } from '@/types/agent';
import type { Channel } from '@/types/integration';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';

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
    let cancelled = false;
    setLoadingNumbers(true);
    listChannelPhoneNumbers(channelId)
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
  }, [open, channelId]);

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

  const selectedCount = selected.size;
  const hasNumbers = numbers.length > 0;

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title="Assign phone numbers"
      hideFooter
      width="sm:max-w-md"
    >
      <div className="flex flex-col gap-4">
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
          placeholder="Select a service provider"
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

        <div className="flex flex-col gap-1.5">
          <p className="text-sm font-medium text-foreground">Phone numbers</p>
          <div className="rounded-xl border border-border/70">
            {loadingNumbers ? (
              <div className="flex items-center gap-2 px-3 py-6 text-sm text-muted-foreground">
                <Loader2 className="size-4 animate-spin" />
                Loading numbers…
              </div>
            ) : !channelId ? (
              <div className="px-3 py-6 text-center text-sm text-muted-foreground">
                Choose a channel to see its numbers.
              </div>
            ) : !hasNumbers ? (
              <div className="px-3 py-6 text-center text-sm text-muted-foreground">
                No phone numbers found. Please configure your integration first.
              </div>
            ) : (
              <ul className="max-h-[260px] divide-y divide-border/60 overflow-y-auto">
                {numbers.map((n) => {
                  const k = keyOf(n.channel_id, n.number);
                  const isSelected = selected.has(k);
                  const takenByOther =
                    !!n.assigned_to &&
                    !currentlyAssigned.some(
                      (a) => a.channel_id === n.channel_id && a.number === n.number,
                    );
                  return (
                    <li key={k}>
                      <CustomButton
                        type="text"
                        onClick={() => !takenByOther && toggleNumber(n)}
                        disabled={takenByOther}
                        title={takenByOther ? `In use by ${n.assigned_to?.agent_name}` : undefined}
                        className={cn(
                          'flex h-auto w-full items-center justify-between gap-3 rounded-none px-3 py-2.5 text-left',
                          isSelected && 'bg-primary/5',
                        )}
                      >
                        <div className="flex min-w-0 items-center gap-2.5">
                          <span
                            className={cn(
                              'flex size-4 shrink-0 items-center justify-center rounded border transition-colors',
                              isSelected
                                ? 'border-primary bg-primary text-primary-foreground'
                                : 'border-border bg-background text-transparent',
                            )}
                          >
                            <Check className="size-3" />
                          </span>
                          <div className="flex min-w-0 flex-col items-start gap-0.5">
                            <span className="truncate text-sm font-medium text-foreground">
                              {n.number}
                            </span>
                            {n.label && (
                              <span className="truncate text-[11px] text-muted-foreground">
                                {n.label}
                              </span>
                            )}
                          </div>
                        </div>
                        {takenByOther && (
                          <Badge
                            variant="secondary"
                            className="shrink-0 px-1.5 text-[10px] capitalize"
                          >
                            In use
                          </Badge>
                        )}
                      </CustomButton>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>

        <div className="flex items-center justify-end gap-2">
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
    </CustomModal>
  );
}

function titleCase(s: string): string {
  return s.toLowerCase().replace(/\b([a-z])/g, (m) => m.toUpperCase());
}
