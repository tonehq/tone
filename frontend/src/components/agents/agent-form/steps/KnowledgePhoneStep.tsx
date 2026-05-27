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
          <div className="rounded-xl border border-dashed border-border/70 py-5 text-center text-sm text-muted-foreground">
            No phone numbers assigned yet.
          </div>
        )}
        {phoneNumbers.length > 0 && (
          <ul className="divide-y divide-border/60 overflow-hidden rounded-xl border border-border/70 bg-card">
            {phoneNumbers.map((row) => {
              const channel = channelById.get(row.channel_id);
              return (
                <li
                  key={`${row.channel_id}|${row.number}`}
                  className="flex items-center justify-between gap-3 px-3 py-2.5"
                >
                  <div className="flex min-w-0 items-center gap-3">
                    <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <Phone className="size-3.5" />
                    </span>
                    <div className="flex min-w-0 flex-col">
                      <span className="truncate text-sm font-medium text-foreground">
                        {row.number}
                      </span>
                      <span className="truncate text-[11px] text-muted-foreground">
                        {channel ? `${channel.name} · ${channel.channel_type}` : 'Unknown channel'}
                        {row.label ? ` · ${row.label}` : ''}
                      </span>
                    </div>
                  </div>
                  <CustomButton
                    type="text"
                    size="icon-xs"
                    onClick={() => removeAssignedNumber(row.number, row.channel_id)}
                    aria-label={`Remove ${row.number}`}
                    className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
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
