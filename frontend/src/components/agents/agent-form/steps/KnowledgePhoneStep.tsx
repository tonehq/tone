'use client';

import {
  AlertCircle,
  Check,
  FileText,
  Loader2,
  Phone,
  PhoneIncoming,
  Upload,
  X,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useFormContext, useWatch } from 'react-hook-form';

import SectionCard, { ACCENTS } from '@/components/agents/agent-form/SectionCard';
import AssignPhoneNumberModal from '@/components/agents/agent-form/steps/AssignPhoneNumberModal';
import KnowledgeBaseUploadModal from '@/components/agents/agent-form/steps/KnowledgeBaseUploadModal';
import { CustomButton, SearchBar } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import { listChannels } from '@/services/channelService';
import { listKnowledgeBase } from '@/services/knowledgeBaseService';
import type { KnowledgeBaseUpload } from '@/services/knowledgeBaseService';
import type { AgentFormState, AgentPhoneNumberInput } from '@/types/agent';
import type { Channel } from '@/types/integration';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { formatPhoneWithDash, getCountryIso2FromPhone } from '@/utils/phoneUtils';
import * as FlagIcons from 'country-flag-icons/react/3x2';

type FlagKey = keyof typeof FlagIcons;

const PAGE_SIZE = 30;

interface KnowledgePhoneStepProps {
  /** Current agent ID when editing. Null while the agent hasn't been
   * created yet — upload is gated behind this because the KB endpoint
   * requires an agent_id to attach the new file. */
  agentId: string | null;
}

export default function KnowledgePhoneStep({ agentId }: KnowledgePhoneStepProps) {
  const { control, setValue } = useFormContext<AgentFormState>();
  const uploadIds = useWatch({ control, name: 'upload_ids' }) ?? [];
  const phoneNumbers = useWatch({ control, name: 'phone_numbers' }) ?? [];

  const [uploadOpen, setUploadOpen] = useState(false);

  // ─── knowledge base ──────────────────────────────────────────────────────
  const [kbSearch, setKbSearch] = useState('');
  const [kbItems, setKbItems] = useState<KnowledgeBaseUpload[]>([]);
  const [kbLoading, setKbLoading] = useState(false);

  const refreshKb = useCallback(async () => {
    setKbLoading(true);
    try {
      // Show both ready and still-processing docs so freshly uploaded files
      // appear in the grid immediately. The row UI surfaces the status so
      // the user can tell which ones aren't usable yet.
      const res = await listKnowledgeBase({
        search: kbSearch.trim() || undefined,
        page: 1,
        page_size: PAGE_SIZE,
        sort_by: '-updated_at',
      });
      setKbItems(res.items);
    } catch (err) {
      handleApiError(err);
    } finally {
      setKbLoading(false);
    }
  }, [kbSearch]);

  useEffect(() => {
    refreshKb();
  }, [refreshKb]);

  const toggleUpload = (id: string) => {
    const set = new Set(uploadIds);
    if (set.has(id)) set.delete(id);
    else set.add(id);
    setValue('upload_ids', Array.from(set), { shouldDirty: true });
  };

  const handleUploaded = useCallback(
    async (newIds: string[]) => {
      // Auto-select the freshly uploaded docs and refetch the list so they
      // appear in the grid without the user having to search for them.
      const merged = Array.from(new Set([...uploadIds, ...newIds]));
      setValue('upload_ids', merged, { shouldDirty: true });
      await refreshKb();
    },
    [uploadIds, setValue, refreshKb],
  );

  // ─── channels + phone numbers ────────────────────────────────────────────
  const [channels, setChannels] = useState<Channel[]>([]);
  const [channelsLoading, setChannelsLoading] = useState(false);
  const [assignOpen, setAssignOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setChannelsLoading(true);
    listChannels()
      .then((rows) => {
        if (cancelled) return;
        setChannels(rows);
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
      {/* Knowledge base */}
      <SectionCard
        icon={<FileText className="size-3.5" strokeWidth={2.25} />}
        iconClassName={ACCENTS.indigo}
        title="Knowledge base"
        description="Attach uploaded documents so the agent can ground its answers."
        action={
          <div className="flex items-center gap-2">
            {uploadIds.length > 0 && (
              <Badge variant="secondary" className="h-5 px-2 text-[11px] tabular-nums">
                {uploadIds.length} attached
              </Badge>
            )}
            <CustomButton
              type="default"
              size="sm"
              icon={<Upload className="size-3.5" />}
              onClick={() => setUploadOpen(true)}
            >
              Upload
            </CustomButton>
          </div>
        }
      >
        {!agentId && (
          <p className="text-[11px] text-muted-foreground">
            Uploads here are queued and attached to the agent automatically when you save.
          </p>
        )}
        <SearchBar
          placeholder="Search documents..."
          value={kbSearch}
          onSearch={setKbSearch}
          debounceMs={300}
          containerClassName="max-w-md"
        />
        <div className="grid gap-2 sm:grid-cols-2">
          {kbLoading &&
            Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="h-[64px] animate-pulse rounded-xl border border-border/40 bg-muted/40"
              />
            ))}
          {!kbLoading && kbItems.length === 0 && (
            <div className="col-span-full rounded-lg border border-dashed border-border/70 py-6 text-center text-sm text-muted-foreground">
              No documents found. Upload some from the Knowledge Base page.
            </div>
          )}
          {!kbLoading &&
            kbItems.map((doc) => {
              const selected = uploadIds.includes(doc.id);
              const isProcessing = doc.status === 'processing' || doc.status === 'pending';
              const isFailed = doc.status === 'failed';
              return (
                <CustomButton
                  key={doc.id}
                  type="text"
                  onClick={() => toggleUpload(doc.id)}
                  title={doc.file_name}
                  className={cn(
                    'flex h-auto w-full min-w-0 items-start justify-between gap-3 overflow-hidden rounded-xl border p-3 text-left transition-colors',
                    selected
                      ? 'border-primary/60 bg-primary/5'
                      : 'border-border/70 hover:border-border',
                  )}
                >
                  <div className="flex min-w-0 flex-1 flex-col items-start gap-1">
                    <span className="flex w-full min-w-0 items-center gap-2 text-sm font-medium text-foreground">
                      <FileText className="size-3.5 shrink-0 text-muted-foreground" />
                      <span className="min-w-0 flex-1 truncate">{doc.file_name}</span>
                    </span>
                    <span className="flex min-w-0 items-center gap-1.5 truncate text-xs text-muted-foreground">
                      {(doc.size_bytes / 1024).toFixed(0)} KB · {doc.file_type}
                      {isProcessing && (
                        <span className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-400">
                          <Loader2 className="size-3 animate-spin" />
                          Processing
                        </span>
                      )}
                      {isFailed && (
                        <span className="inline-flex items-center gap-1 text-destructive">
                          <AlertCircle className="size-3" />
                          Failed
                        </span>
                      )}
                    </span>
                  </div>
                  <span
                    className={cn(
                      'mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full border transition-colors',
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
        </div>
      </SectionCard>

      {/* Phone numbers */}
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
          disabled={channelsLoading || channels.length === 0}
          className="self-start"
          title={channels.length === 0 ? 'Connect a channel first under Integrations.' : undefined}
        >
          {phoneNumbers.length === 0 ? 'Assign number' : 'Manage numbers'}
        </CustomButton>
        {channels.length === 0 && !channelsLoading && (
          <p className="text-[11px] text-muted-foreground">
            <Phone className="mr-1 inline size-3" />
            Connect a phone channel under Integrations to start assigning numbers.
          </p>
        )}
      </SectionCard>

      <KnowledgeBaseUploadModal
        open={uploadOpen}
        agentId={agentId}
        onClose={() => setUploadOpen(false)}
        onUploaded={handleUploaded}
      />

      <AssignPhoneNumberModal
        open={assignOpen}
        onClose={() => setAssignOpen(false)}
        channels={channels}
        channelsLoading={channelsLoading}
        currentlyAssigned={phoneNumbers}
        onAssign={handleAssignedFromModal}
      />
    </div>
  );
}
