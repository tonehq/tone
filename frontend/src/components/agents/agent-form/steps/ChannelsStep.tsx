'use client';

import { Check, Phone, PhoneIncoming, Radio, Video, X } from 'lucide-react';
import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useFormContext, useWatch } from 'react-hook-form';

import SectionCard, { ACCENTS } from '@/components/agents/agent-form/SectionCard';
import AssignPhoneNumberModal from '@/components/agents/agent-form/steps/AssignPhoneNumberModal';
import { CustomButton } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import { listChannels } from '@/services/channelService';
import type { AgentFormState, AgentPhoneNumberInput } from '@/types/agent';
import type { Channel } from '@/types/integration';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { formatPhoneWithDash, getCountryIso2FromPhone } from '@/utils/phoneUtils';
import * as FlagIcons from 'country-flag-icons/react/3x2';

type FlagKey = keyof typeof FlagIcons;

const WEB_PROVIDERS: { type: string; label: string }[] = [
  { type: 'livekit', label: 'LiveKit' },
  { type: 'daily', label: 'Daily' },
];

const WEB_CHANNEL_TYPES = WEB_PROVIDERS.map((p) => p.type);

const WEB_ICONS: Record<string, React.ReactNode> = {
  livekit: <Radio className="size-4" strokeWidth={2.25} />,
  daily: <Video className="size-4" strokeWidth={2.25} />,
};

export default function ChannelsStep() {
  const { control, setValue } = useFormContext<AgentFormState>();
  const phoneNumbers = useWatch({ control, name: 'phone_numbers' }) ?? [];
  const webChannelIds = useWatch({ control, name: 'web_channel_ids' }) ?? [];

  const [channels, setChannels] = useState<Channel[]>([]);
  const [channelsLoading, setChannelsLoading] = useState(false);
  const [assignOpen, setAssignOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setChannelsLoading(true);
    listChannels()
      .then((rows) => {
        if (!cancelled) setChannels(rows);
      })
      .catch((err) => {
        if (!cancelled) handleApiError(err);
      })
      .finally(() => {
        if (!cancelled) setChannelsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const channelById = useMemo(() => {
    const map = new Map<string, Channel>();
    channels.forEach((c) => map.set(c.id, c));
    return map;
  }, [channels]);

  const webChannels = useMemo(
    () => channels.filter((c) => WEB_CHANNEL_TYPES.includes(c.channel_type)),
    [channels],
  );
  const phoneChannels = useMemo(
    () => channels.filter((c) => !WEB_CHANNEL_TYPES.includes(c.channel_type)),
    [channels],
  );

  const configuredWebTypes = new Set(webChannels.map((c) => c.channel_type));
  const missingWebProviders = WEB_PROVIDERS.filter((p) => !configuredWebTypes.has(p.type));

  const toggleWebChannel = (id: string) => {
    const set = new Set(webChannelIds);
    if (set.has(id)) set.delete(id);
    else set.add(id);
    setValue('web_channel_ids', Array.from(set), { shouldDirty: true });
  };

  const handleAssignedFromModal = useCallback(
    (rows: AgentPhoneNumberInput[]) => {
      setValue('phone_numbers', rows, { shouldDirty: true });
    },
    [setValue],
  );

  const removeAssignedNumber = (number: string, channelId: string) => {
    setValue(
      'phone_numbers',
      phoneNumbers.filter((p) => !(p.number === number && p.channel_id === channelId)),
      { shouldDirty: true },
    );
  };

  return (
    <div className="flex flex-col gap-4">
      <SectionCard
        icon={<Radio className="size-3.5" strokeWidth={2.25} />}
        iconClassName={ACCENTS.sky}
        title="Web calls"
        description="Enable in-browser voice calls. Each enabled provider gives this agent a shareable call link."
        action={
          webChannelIds.length > 0 ? (
            <Badge variant="secondary" className="h-5 px-2 text-[11px] tabular-nums">
              {webChannelIds.length} enabled
            </Badge>
          ) : null
        }
      >
        <div className="grid gap-2 sm:grid-cols-2">
          {webChannels.map((c) => {
            const selected = webChannelIds.includes(c.id);
            return (
              <CustomButton
                key={c.id}
                type="text"
                onClick={() => toggleWebChannel(c.id)}
                className={cn(
                  'flex h-auto w-full min-w-0 items-center justify-between gap-3 rounded-xl border p-3 text-left transition-colors',
                  selected
                    ? 'border-primary/60 bg-primary/5'
                    : 'border-border/70 hover:border-border',
                )}
              >
                <span className="flex min-w-0 items-center gap-2.5">
                  <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/8 text-primary ring-1 ring-primary/10">
                    {WEB_ICONS[c.channel_type] ?? <Radio className="size-4" />}
                  </span>
                  <span className="flex min-w-0 flex-col gap-0.5">
                    <span className="truncate text-sm font-medium text-foreground">{c.name}</span>
                    <Badge
                      variant="secondary"
                      className="h-4 w-fit px-1.5 text-[9px] font-medium uppercase tracking-wide"
                    >
                      {c.channel_type}
                    </Badge>
                  </span>
                </span>
                <span
                  className={cn(
                    'flex size-5 shrink-0 items-center justify-center rounded-full border transition-colors',
                    selected
                      ? 'border-primary bg-primary text-primary-foreground'
                      : 'border-border bg-background text-transparent',
                  )}
                >
                  <Check className="size-3" />
                </span>
              </CustomButton>
            );
          })}
          {!channelsLoading &&
            missingWebProviders.map((p) => (
              <div
                key={p.type}
                className="flex min-w-0 items-center gap-2.5 rounded-xl border border-dashed border-border/60 bg-muted/20 p-3 opacity-90"
              >
                <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                  {WEB_ICONS[p.type] ?? <Radio className="size-4" />}
                </span>
                <span className="flex min-w-0 flex-col gap-0.5">
                  <span className="truncate text-sm font-medium text-muted-foreground">
                    {p.label}
                  </span>
                  <span className="text-[11px] text-muted-foreground">
                    Add API keys in{' '}
                    <Link
                      href="/integrations"
                      className="font-medium text-primary underline-offset-2 hover:underline"
                    >
                      Integrations
                    </Link>{' '}
                    to enable.
                  </span>
                </span>
              </div>
            ))}
        </div>
        {webChannelIds.length > 0 && (
          <p className="text-[11px] text-muted-foreground">
            Save and publish the agent to get the shareable call link — it appears next to the agent
            name.
          </p>
        )}
      </SectionCard>

      <SectionCard
        icon={<Phone className="size-3.5" strokeWidth={2.25} />}
        iconClassName={ACCENTS.emerald}
        title="Phone numbers"
        description="Numbers that route to this agent."
        action={
          phoneNumbers.length > 0 ? (
            <Badge variant="secondary" className="h-5 px-2 text-[11px] tabular-nums">
              {phoneNumbers.length} assigned
            </Badge>
          ) : null
        }
      >
        {phoneNumbers.length === 0 && (
          <div className="flex flex-col items-center gap-1.5 rounded-xl border border-dashed border-border/70 bg-muted/20 px-4 py-6 text-center">
            <span className="flex size-8 items-center justify-center rounded-full bg-muted text-muted-foreground">
              <PhoneIncoming className="size-4" />
            </span>
            <p className="text-sm font-medium text-foreground">No phone numbers assigned</p>
            <p className="text-[11px] text-muted-foreground">
              Click below to pick from your connected providers.
            </p>
          </div>
        )}
        {phoneNumbers.length > 0 && (
          <ul className="grid gap-2 sm:grid-cols-2">
            {phoneNumbers.map((row) => {
              const channel = channelById.get(row.channel_id);
              const iso2 = getCountryIso2FromPhone(row.number);
              const FlagComponent = iso2
                ? (FlagIcons[iso2 as FlagKey] as
                    | React.ComponentType<React.SVGProps<SVGSVGElement>>
                    | undefined)
                : undefined;
              return (
                <li
                  key={`${row.channel_id}|${row.number}`}
                  className={cn(
                    'group relative flex items-center gap-3 overflow-hidden rounded-xl border border-border/70 bg-card px-3 py-2.5 transition-all',
                    'hover:border-primary/40 hover:shadow-sm',
                  )}
                >
                  <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/8 text-primary ring-1 ring-primary/10">
                    <Phone className="size-4" strokeWidth={2.25} />
                  </span>
                  <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                    <span className="flex min-w-0 items-center gap-2">
                      {FlagComponent ? (
                        <FlagComponent
                          className="h-3 w-[18px] shrink-0 rounded-[2px] object-cover shadow-[0_0_0_0.5px_rgba(0,0,0,0.08)]"
                          aria-label={iso2 ?? undefined}
                        />
                      ) : null}
                      <span className="truncate text-sm font-semibold tabular-nums text-foreground">
                        {formatPhoneWithDash(row.number)}
                      </span>
                    </span>
                    <span className="flex min-w-0 items-center gap-1.5 truncate text-[11px] text-muted-foreground">
                      {channel ? (
                        <>
                          <span className="truncate font-medium text-foreground/80">
                            {channel.name}
                          </span>
                          <Badge
                            variant="secondary"
                            className="h-4 shrink-0 px-1.5 text-[9px] font-medium uppercase tracking-wide"
                          >
                            {channel.channel_type}
                          </Badge>
                          {row.label && <span className="truncate">· {row.label}</span>}
                        </>
                      ) : (
                        <span>Unknown channel</span>
                      )}
                    </span>
                  </div>
                  <CustomButton
                    type="text"
                    size="icon-xs"
                    onClick={() => removeAssignedNumber(row.number, row.channel_id)}
                    aria-label={`Remove ${row.number}`}
                    className={cn(
                      'shrink-0 text-muted-foreground transition-all',
                      'opacity-60 hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100',
                    )}
                  >
                    <X className="size-4" />
                  </CustomButton>
                </li>
              );
            })}
          </ul>
        )}
        <CustomButton
          type="default"
          icon={<PhoneIncoming className="size-4" />}
          onClick={() => setAssignOpen(true)}
          disabled={channelsLoading || phoneChannels.length === 0}
          className="self-start"
          title={
            phoneChannels.length === 0 ? 'Connect a channel first under Integrations.' : undefined
          }
        >
          {phoneNumbers.length === 0 ? 'Assign number' : 'Manage numbers'}
        </CustomButton>
        {phoneChannels.length === 0 && !channelsLoading && (
          <p className="text-[11px] text-muted-foreground">
            <Phone className="mr-1 inline size-3" />
            Connect a phone channel under Integrations to start assigning numbers.
          </p>
        )}
      </SectionCard>

      <AssignPhoneNumberModal
        open={assignOpen}
        onClose={() => setAssignOpen(false)}
        channels={phoneChannels}
        channelsLoading={channelsLoading}
        currentlyAssigned={phoneNumbers}
        onAssign={handleAssignedFromModal}
      />
    </div>
  );
}
