'use client';

import { AlertCircle, Check, FileText, Loader2, Upload } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useFormContext, useWatch } from 'react-hook-form';

import SectionCard, { ACCENTS } from '@/components/agents/agent-form/SectionCard';
import KnowledgeBaseUploadModal from '@/components/agents/agent-form/steps/KnowledgeBaseUploadModal';
import { useAgentEditor } from '@/components/agents/AgentEditorContext';
import { CustomButton, SearchBar, SelectInput } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import { useIngestionRuns, useSetAgentKbActiveRun } from '@/lib/api/ingestion-runs';
import { listKnowledgeBase } from '@/services/knowledgeBaseService';
import type { KnowledgeBaseUpload } from '@/services/knowledgeBaseService';
import type { AgentFormState } from '@/types/agent';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

const PAGE_SIZE = 30;
const KB_DEFAULT_VALUE = '__kb_default__';

interface KnowledgePhoneStepProps {
  /** Current agent ID when editing. Null while the agent hasn't been
   * created yet — upload is gated behind this because the KB endpoint
   * requires an agent_id to attach the new file. */
  agentId: string | null;
}

export default function KnowledgePhoneStep({ agentId }: KnowledgePhoneStepProps) {
  const { control, setValue } = useFormContext<AgentFormState>();
  const uploadIds = useWatch({ control, name: 'upload_ids' }) ?? [];
  const { detail } = useAgentEditor();

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

  // Per-KB active-run map keyed by upload_id. Seeded from AgentDetail so the
  // dropdown shows whatever this agent is currently pinned to, then updated
  // fire-on-change via `useSetAgentKbActiveRun` — no form-state coupling.
  const initialPinByUploadId = useMemo(() => {
    const map = new Map<string, { kbId: string; runId: string | null }>();
    for (const d of detail?.documents ?? []) {
      if (d.knowledge_base_id) {
        map.set(d.id, {
          kbId: d.knowledge_base_id,
          runId: d.active_ingestion_pipeline_run_id ?? null,
        });
      }
    }
    return map;
  }, [detail]);

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
                <div
                  key={doc.id}
                  className={cn(
                    'flex flex-col gap-2 overflow-hidden rounded-xl border p-3 transition-colors',
                    selected
                      ? 'border-primary/60 bg-primary/5'
                      : 'border-border/70 hover:border-border',
                  )}
                >
                  <CustomButton
                    type="text"
                    onClick={() => toggleUpload(doc.id)}
                    title={doc.file_name}
                    className="flex h-auto w-full min-w-0 items-start justify-between gap-3 !p-0 text-left"
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

                  {/* Per-KB active-run picker. Only rendered for attached KBs
                      the agent is already persisted on — a brand-new attach
                      only becomes pinnable after the first save creates the
                      AgentKnowledgeBase row. */}
                  {selected && agentId && initialPinByUploadId.has(doc.id) && (
                    <ActiveRunPicker
                      uploadId={doc.id}
                      agentId={agentId}
                      kbId={initialPinByUploadId.get(doc.id)!.kbId}
                      initialRunId={initialPinByUploadId.get(doc.id)!.runId}
                    />
                  )}
                </div>
              );
            })}
        </div>
      </SectionCard>

      <KnowledgeBaseUploadModal
        open={uploadOpen}
        agentId={agentId}
        onClose={() => setUploadOpen(false)}
        onUploaded={handleUploaded}
      />
    </div>
  );
}

// ─── per-KB active-run picker ─────────────────────────────────────────────
// Small inline widget rendered in its own component so ``useIngestionRuns``
// can be called once per attached KB without breaking Rules of Hooks. Fires
// the "set/clear pin" mutation on change. Fire-on-change (not form-batched)
// keeps the concern local to this attachment and avoids plumbing new fields
// through ``AgentFormState`` / ``formStateToUpsertPayload``.
function ActiveRunPicker({
  uploadId,
  agentId,
  kbId,
  initialRunId,
}: {
  uploadId: string;
  agentId: string;
  kbId: string;
  initialRunId: string | null;
}) {
  const [value, setValue] = useState<string>(initialRunId ?? KB_DEFAULT_VALUE);
  const setAgentPin = useSetAgentKbActiveRun();

  useEffect(() => {
    setValue(initialRunId ?? KB_DEFAULT_VALUE);
  }, [initialRunId]);

  // Cached + polled by React Query — shared with the standalone Ingestion
  // Runs tab so a user hopping between the two views doesn't pay a second
  // fetch. 50 recent ready runs is more than enough for the picker;
  // browsing full history is done on the runs tab.
  const { data, isLoading } = useIngestionRuns(uploadId, {
    page_no: 1,
    page_size: 50,
    status_filter: ['ready'],
    sort_by: 'run_number',
    sort_order: 'desc',
  });
  const runs = data?.data ?? [];

  const options = useMemo(
    () => [
      { value: KB_DEFAULT_VALUE, label: 'Use KB default' },
      ...runs.map((r) => ({
        value: r.id,
        label: `Run ${r.run_number} · ${r.parser} / ${r.embedding_model} · ${r.embedding_dimensions}D`,
      })),
    ],
    [runs],
  );

  const handleChange = async (next: string) => {
    const previous = value;
    setValue(next); // optimistic
    const runId = next === KB_DEFAULT_VALUE ? null : next;
    try {
      await setAgentPin.mutateAsync({ agentId, kbId, runId });
      showToast.success(runId ? 'Run pinned for this agent' : 'Reverted to KB default');
    } catch (err) {
      setValue(previous); // roll back
      handleApiError(err);
    }
  };

  return (
    <div className="border-t border-border/40 pt-2">
      <SelectInput
        name={`kb-run-${uploadId}`}
        label="Run"
        options={options}
        value={value}
        onValueChange={handleChange}
        loading={isLoading}
        disabled={setAgentPin.isPending}
        size="sm"
      />
    </div>
  );
}
