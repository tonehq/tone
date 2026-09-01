'use client';

import {
  ArrowLeft,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Clock,
  Download,
  Folder as FolderIcon,
  Gauge,
  History,
  Loader2,
  MinusCircle,
  MoreVertical,
  Pencil,
  Play,
  Sparkles,
  Trash2,
  Upload,
  Wrench,
  X,
  XCircle,
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';

import SectionCard from '@/components/agents/agent-form/SectionCard';
import ConfirmDeleteModal from '@/components/contacts/shared/ConfirmDeleteModal';
import {
  CustomButton,
  CustomDrawer,
  CustomModal,
  CustomPopover,
  CustomTab,
  SearchBar,
  SelectInput,
  TextAreaField,
  TextInput,
} from '@/components/shared';
import { formatIngestionError } from '@/components/knowledge-base/ingestionErrorFormat';
import { Checkbox } from '@/components/ui/checkbox';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { TabItem } from '@/components/shared';
import {
  useAgentLlmEvalFolders,
  useAgentLlmEvalRunDetail,
  useAgentLlmEvalRuns,
  useAgentLlmEvalScenarios,
  useCreateAgentLlmEvalFolder,
  useCreateAgentLlmEvalScenario,
  useCreateAgentLlmEvalScenariosBulk,
  useDeleteAgentLlmEvalFolder,
  useDeleteAgentLlmEvalScenario,
  useDeleteAgentLlmEvalScenariosBulk,
  useGenerateAgentLlmEvalScenarios,
  useRenameAgentLlmEvalFolder,
  useTriggerAgentLlmEvalRun,
  useUpdateAgentLlmEvalScenario,
  useUploadAgentLlmEvalScenariosCsv,
} from '@/lib/api/agentLlmEvals';
import type {
  AgentLlmEvalBatchStatus,
  AgentLlmEvalFolder,
  AgentLlmEvalRunSummary,
  AgentLlmEvalScenario,
  AgentLlmEvalScenarioSource,
  AgentLlmEvalScoredScenario,
  AgentLlmEvalVerdict,
  GeneratedScenario,
  ScenarioInput,
  ScenarioPatch,
} from '@/types/agentLlmEval';
import { cn } from '@/utils/cn';
import { formatDate } from '@/utils/date';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

// ── Shared verdict chip ─────────────────────────────────────────────────

const VERDICT_STYLES: Record<
  AgentLlmEvalVerdict,
  { label: string; className: string; icon: React.ReactNode }
> = {
  PASS: {
    label: 'Pass',
    className:
      'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 ring-1 ring-emerald-500/20',
    icon: <CheckCircle2 className="size-3" />,
  },
  PARTIAL: {
    label: 'Partial',
    className: 'bg-amber-500/10 text-amber-700 dark:text-amber-400 ring-1 ring-amber-500/20',
    icon: <MinusCircle className="size-3" />,
  },
  FAIL: {
    label: 'Fail',
    className: 'bg-destructive/10 text-destructive ring-1 ring-destructive/20',
    icon: <XCircle className="size-3" />,
  },
};

function VerdictChip({ verdict }: { verdict: AgentLlmEvalVerdict | null | undefined }) {
  const key = (verdict as AgentLlmEvalVerdict) ?? 'FAIL';
  const s = VERDICT_STYLES[key] ?? VERDICT_STYLES.FAIL;
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium',
        s.className,
      )}
    >
      {s.icon}
      {verdict ? s.label : '—'}
    </span>
  );
}

// ── Run status chip ────────────────────────────────────────────────────

// Chip for the Runs tab's status column. Same visual grammar as
// ``VerdictChip`` so the two feel like siblings. Terminal states are
// definitive (Completed / Failed); non-terminal states use motion cues
// (spinner for running, clock for pending) so the eye picks them out
// without a colour scan.
const RUN_STATUS_STYLES: Record<
  AgentLlmEvalBatchStatus,
  { label: string; className: string; icon: React.ReactNode }
> = {
  pending: {
    label: 'Pending',
    className: 'bg-muted text-muted-foreground ring-1 ring-border',
    icon: <Clock className="size-3" />,
  },
  running: {
    label: 'Running',
    className: 'bg-amber-500/10 text-amber-700 dark:text-amber-400 ring-1 ring-amber-500/20',
    icon: <Loader2 className="size-3 animate-spin" />,
  },
  completed: {
    label: 'Completed',
    className:
      'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 ring-1 ring-emerald-500/20',
    icon: <CheckCircle2 className="size-3" />,
  },
  failed: {
    label: 'Failed',
    className: 'bg-destructive/10 text-destructive ring-1 ring-destructive/20',
    icon: <XCircle className="size-3" />,
  },
};

function RunStatusChip({ status }: { status: AgentLlmEvalBatchStatus }) {
  const s = RUN_STATUS_STYLES[status] ?? RUN_STATUS_STYLES.pending;
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium',
        s.className,
      )}
    >
      {s.icon}
      {s.label}
    </span>
  );
}

// Terminal states = drawer is safe to open (results are persisted).
// Non-terminal rows (pending / running) suppress the drawer and show a
// muted "Scoring N of M" progress readout in the Result column instead.
const RUN_TERMINAL_STATUSES: ReadonlySet<AgentLlmEvalBatchStatus> = new Set([
  'completed',
  'failed',
]);

// ── Folder scope ────────────────────────────────────────────────────────

// The selected folder in the sidebar. ``null`` = "All", non-null = a
// folder id (folders are first-class rows). Every scenario belongs to a
// real folder — there is no "Uncategorized" bucket.
export type FolderScope = null | string;

// Sub-tab identity inside the LLM Evals section. Kept as a named union so
// the tab key + the state setter agree on the exact strings — a typo in
// one place fails at compile time instead of silently rendering nothing.
type LlmEvalsView = 'folders' | 'runs';

// ── Sample CSV download ─────────────────────────────────────────────────
//
// The CSV importer on the backend accepts these column headers (see
// ``_CSV_ALLOWED_COLUMNS`` in ``core/services/evals/agent_llm/scenario_service.py``).
// ``scenario_key`` and ``prompt`` are required; the rest are optional.
// Kept inline in this file — the LLM Evals import flow is the only caller,
// and the header list needs to stay in lock-step with the backend allow-list.
const SAMPLE_CSV_HEADERS = [
  'scenario_key',
  'prompt',
  'expected_answer',
  'persona_criteria',
  'instruction_criteria',
  'tags',
  'folder',
] as const;

const SAMPLE_CSV_ROWS: readonly (readonly string[])[] = [
  [
    'happy_path_booking',
    'I would like to book a deluxe room for two from June 10th to June 12th.',
    'Confirms availability and reads back the dates and room type.',
    'Warm, professional, concise',
    'Do not invent a price; confirm the reservation before ending the call.',
    'booking,happy_path',
    'Booking',
  ],
  [
    'refund_request',
    'I want a refund for my last stay because the room was not clean.',
    'Acknowledges the issue, apologizes, and offers a refund per policy.',
    'Empathetic, calm',
    'Never blame the guest; always offer a resolution.',
    'refund,complaint',
    'Support',
  ],
  [
    'out_of_scope',
    "Can you tell me tomorrow's weather forecast?",
    'Politely declines and redirects to hotel-related topics.',
    'Polite, brief',
    'Do not answer questions unrelated to the hotel.',
    'guardrail',
    '',
  ],
];

/** Build the sample CSV text. RFC 4180 quoting: wrap any cell containing a
 * comma, quote, or newline in double quotes and double up embedded quotes. */
function buildSampleCsv(): string {
  const escape = (v: string) => (/[",\n\r]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v);
  const lines = [SAMPLE_CSV_HEADERS, ...SAMPLE_CSV_ROWS].map((row) => row.map(escape).join(','));
  return `${lines.join('\n')}\n`;
}

/** Trigger a browser download for the sample CSV template. */
function downloadSampleCsv() {
  const blob = new Blob([buildSampleCsv()], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'llm-evals-scenarios-sample.csv';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

// Sentinel option value used by ``FolderPicker``'s inline SelectInput to
// represent the "Create new folder…" affordance. Any string not otherwise
// a folder id is fine; using a reserved token avoids clashing with a
// real UUID.
const NEW_FOLDER_OPTION_VALUE = '__new_folder__';

// ── Main step ───────────────────────────────────────────────────────────

export default function LlmEvalsStep({ agentId }: { agentId: string | null }) {
  // Create mode: agent isn't saved yet. Render an empty state instead of
  // hiding the section entirely, so users discover the feature and know
  // exactly what to do first.
  if (!agentId) {
    return <LlmEvalsSaveFirstEmptyState />;
  }
  return <LlmEvalsStepBody agentId={agentId} />;
}

function LlmEvalsSaveFirstEmptyState() {
  return (
    <SectionCard
      icon={<Gauge className="size-4" />}
      iconClassName="bg-violet-500/10 text-violet-700 dark:text-violet-400 ring-violet-500/20"
      title="LLM Evals"
      description="Score this agent's LLM output against your scenarios."
    >
      <div className="rounded-md border border-dashed border-border/60 bg-muted/20 p-6 text-center">
        <p className="text-sm font-medium text-foreground">Save the agent first</p>
        <p className="mx-auto mt-1 max-w-md text-[13px] text-muted-foreground">
          LLM evals score this agent&apos;s actual system prompt + LLM configuration. Fill in the
          Prompt and Setup (AI model / provider) sections, click{' '}
          <span className="font-medium text-foreground">Create agent</span>, then come back here to
          add scenarios and run your first eval.
        </p>
      </div>
    </SectionCard>
  );
}

function LlmEvalsStepBody({ agentId }: { agentId: string }) {
  const [search, setSearch] = useState('');
  const [editing, setEditing] = useState<AgentLlmEvalScenario | null>(null);
  const [openCreate, setOpenCreate] = useState(false);
  const [openRun, setOpenRun] = useState(false);
  const [openGenerate, setOpenGenerate] = useState(false);
  const [openRunId, setOpenRunId] = useState<string | null>(null);
  // Delete confirm is routed through the shared ``ConfirmDeleteModal``
  // (Radix-based) so it matches the rest of the app's destructive-action
  // dialogs — instead of a browser-native ``window.confirm``.
  const [pendingDelete, setPendingDelete] = useState<AgentLlmEvalScenario | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Folder scope selector. ``null`` = All (no filter). Non-null = folder id.
  const [selectedFolder, setSelectedFolder] = useState<FolderScope>(null);
  // Folder currently in inline-rename mode (id of the folder being
  // edited). ``null`` = no folder is being renamed. Only one folder can
  // be in edit mode at a time; the card / breadcrumb whose ``id``
  // matches renders ``InlineFolderNameEditor`` in place of the name span.
  const [editingFolderId, setEditingFolderId] = useState<string | null>(null);
  // Folder pending delete (id). Non-null → shared ``ConfirmDeleteModal`` is
  // open with the folder's name + scenario-count impact copy.
  const [pendingDeleteFolderId, setPendingDeleteFolderId] = useState<string | null>(null);
  // New-folder modal state.
  const [openNewFolder, setOpenNewFolder] = useState(false);
  // Bulk-selection for scenarios inside a folder. Persists across pages
  // (Gmail-style — a user selects row A on page 1, paginates, comes back,
  // A is still checked). Cleared when the folder scope changes so
  // selections don't leak across contexts (see the useEffect below).
  const [selectedScenarioIds, setSelectedScenarioIds] = useState<Set<string>>(() => new Set());
  const [pendingBulkDelete, setPendingBulkDelete] = useState(false);
  // Sub-tab inside the LLM Evals section — 'folders' (default: scenario
  // management) vs 'runs' (past run history). Kept as local state; not
  // URL-synced in v1. Promote to a query param later if deep-links needed.
  const [activeView, setActiveView] = useState<LlmEvalsView>('folders');

  // Pagination for the scenarios list inside a folder. Reset back to page 1
  // whenever the folder scope, search query, or any filter changes so the
  // user never lands on an out-of-range page after switching context.
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Source filter for the scenarios-in-folder table. Backend supports it
  // via ``ListScenariosRequest.source`` (exact-match enum). ``null`` is
  // omitted from the request so the "no filter" path is used.
  const [filterSource, setFilterSource] = useState<AgentLlmEvalScenarioSource | null>(null);
  useEffect(() => {
    setPage(1);
  }, [selectedFolder, search, filterSource]);
  // Wipe bulk-selection whenever the user changes context (folder or
  // filters). Keeping a stale selection alive across contexts would let
  // users delete rows they can't currently see — surprising and unsafe.
  useEffect(() => {
    setSelectedScenarioIds(new Set());
  }, [selectedFolder, search, filterSource]);

  // Pagination for the Runs tab. Kept as separate state from the scenarios
  // pager so switching folders doesn't reset the runs page (and vice-versa).
  const [runsPage, setRunsPage] = useState(1);
  const [runsPageSize, setRunsPageSize] = useState(10);

  const scenariosQuery = useAgentLlmEvalScenarios(agentId, {
    search: search || undefined,
    folder_id: selectedFolder ?? undefined,
    // Send the source filter only when set — omitting it entirely so the
    // backend takes its "no filter" fast path and the query key stays
    // compact.
    source: filterSource ?? undefined,
    page_no: page,
    page_size: pageSize,
  });
  const foldersQuery = useAgentLlmEvalFolders(agentId);
  const runsQuery = useAgentLlmEvalRuns(agentId, {
    page_no: runsPage,
    page_size: runsPageSize,
  });
  const uploadCsv = useUploadAgentLlmEvalScenariosCsv(agentId);
  const deleteScenario = useDeleteAgentLlmEvalScenario(agentId);
  const deleteScenariosBulk = useDeleteAgentLlmEvalScenariosBulk(agentId);
  const deleteFolder = useDeleteAgentLlmEvalFolder(agentId);
  const renameFolderMutation = useRenameAgentLlmEvalFolder(agentId);
  const createFolder = useCreateAgentLlmEvalFolder(agentId);
  const triggerRun = useTriggerAgentLlmEvalRun(agentId);

  const scenarios = scenariosQuery.data?.items ?? [];
  const runs = runsQuery.data?.items ?? [];
  const runsTotal = runsQuery.data?.total ?? runs.length;
  const scenarioCount = scenariosQuery.data?.total ?? scenarios.length;
  const folders = foldersQuery.data?.items ?? [];
  const totalScenariosAllFolders = folders.reduce((n, f) => n + f.count, 0);

  // Snap ``page`` back into range whenever the total shrinks below the
  // current page (bulk-delete, filter change, folder-delete side effect).
  // Without this the query keeps requesting an out-of-range page_no and
  // the table shows an empty state the user has no obvious way out of.
  // Only runs after the query returns (``scenariosQuery.data`` truthy)
  // so we don't fight the initial 0-total transition on first load.
  useEffect(() => {
    if (!scenariosQuery.data) return;
    const maxPage = Math.max(1, Math.ceil(scenarioCount / pageSize));
    if (page > maxPage) setPage(maxPage);
  }, [scenarioCount, pageSize, page, scenariosQuery.data]);
  useEffect(() => {
    if (!runsQuery.data) return;
    const maxRunsPage = Math.max(1, Math.ceil(runsTotal / runsPageSize));
    if (runsPage > maxRunsPage) setRunsPage(maxRunsPage);
  }, [runsTotal, runsPageSize, runsPage, runsQuery.data]);

  // Quick-run one folder from a card / breadcrumb. Uses the singular
  // ``folder_id`` field intentionally (single-folder path). Multi-folder
  // runs go through the RunEvalModal with the plural ``folder_ids`` field
  // instead. The two never mix in one request.
  const runFolder = async (folderId: string) => {
    try {
      await triggerRun.mutateAsync({ folder_id: folderId });
      showToast.success(
        'Evaluation started',
        'Your scenarios are running now. Open the Runs tab in a moment to see the results.',
      );
    } catch (error) {
      handleApiError(error);
    }
  };

  // Fire an eval scoped to a single scenario. Reuses the same trigger
  // endpoint the folder / tag / modal flows use — the backend accepts
  // ``scenario_ids`` and narrows the run to exactly those rows (see
  // ``AgentLlmScenarioService.list_scenarios`` + ``TriggerRunRequest``).
  // The toast copy is identical to the other run entry points so users
  // learn one mental model regardless of which surface started the run.
  const runScenario = async (scenario: AgentLlmEvalScenario) => {
    try {
      await triggerRun.mutateAsync({ scenario_ids: [scenario.id] });
      showToast.success(
        'Evaluation started',
        `“${scenario.scenario_key}” is running now. Open the Runs tab in a moment to see the result.`,
      );
    } catch (error) {
      handleApiError(error);
    }
  };

  const handleCsvPick = async (file: File | null) => {
    if (!file) return;
    try {
      const result = await uploadCsv.mutateAsync(file);
      showToast.success(
        'CSV imported',
        `${result.created} scenario${result.created === 1 ? '' : 's'} added.`,
      );
    } catch (error) {
      handleApiError(error);
    }
  };

  const handleDelete = (scenario: AgentLlmEvalScenario) => {
    setPendingDelete(scenario);
  };

  const confirmDelete = async () => {
    if (!pendingDelete) return;
    try {
      await deleteScenario.mutateAsync(pendingDelete.id);
      showToast.success('Scenario deleted');
      setPendingDelete(null);
    } catch (error) {
      handleApiError(error);
      // Keep the modal open on failure so the user can see the error toast
      // and retry without losing their selection.
    }
  };

  const confirmDeleteFolder = async () => {
    if (!pendingDeleteFolderId) return;
    try {
      const result = await deleteFolder.mutateAsync({ folder_id: pendingDeleteFolderId });
      // If the user was drilled into the folder they just deleted, drop
      // back to the folder grid so they don't end up staring at a
      // now-empty scenarios table for a folder that no longer exists.
      if (selectedFolder === pendingDeleteFolderId) {
        setSelectedFolder(null);
      }
      showToast.success(
        'Folder deleted',
        `${result.scenarios_deleted} scenario${result.scenarios_deleted === 1 ? '' : 's'} removed.`,
      );
      setPendingDeleteFolderId(null);
    } catch (error) {
      handleApiError(error);
      // Same rationale as ``confirmDelete`` — keep the modal open so the
      // user can see the error toast and retry.
    }
  };

  const saveRenameFolder = async (nextName: string) => {
    // ``editingFolderId`` should always be set when this fires (it's what
    // opens the editor), but guard defensively — a stale callback from
    // an unmounted card could otherwise send an empty ``folder_id``.
    if (!editingFolderId) return;
    const current = folders.find((f) => f.id === editingFolderId);
    const trimmed = nextName.trim();
    if (!trimmed || !current || trimmed === current.name) {
      setEditingFolderId(null);
      return;
    }
    try {
      await renameFolderMutation.mutateAsync({
        folder_id: editingFolderId,
        new_name: trimmed,
      });
      showToast.success('Folder renamed');
      setEditingFolderId(null);
    } catch (error) {
      handleApiError(error);
      // Keep edit mode open on failure so the user sees the error toast
      // and can retry without losing their typed name.
    }
  };

  const cancelRenameFolder = () => {
    if (renameFolderMutation.isPending) return;
    setEditingFolderId(null);
  };

  const submitNewFolder = async (name: string) => {
    const trimmed = name.trim();
    if (!trimmed) return;
    try {
      await createFolder.mutateAsync({ name: trimmed });
      showToast.success('Folder created');
      setOpenNewFolder(false);
    } catch (error) {
      handleApiError(error);
    }
  };

  const toggleScenarioSelection = (id: string) => {
    setSelectedScenarioIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const togglePageSelection = () => {
    // "Select all" header checkbox toggles the CURRENT page only. If
    // every visible row is already selected, uncheck them (leaving
    // off-page selections untouched); otherwise, add every visible id.
    // Off-page selections persist either way — that's the Gmail
    // convention and it plays nicely with pagination.
    setSelectedScenarioIds((prev) => {
      const next = new Set(prev);
      const pageIds = scenarios.map((s) => s.id);
      const allOnPageSelected = pageIds.length > 0 && pageIds.every((id) => next.has(id));
      if (allOnPageSelected) {
        for (const id of pageIds) next.delete(id);
      } else {
        for (const id of pageIds) next.add(id);
      }
      return next;
    });
  };

  const confirmBulkDelete = async () => {
    const ids = Array.from(selectedScenarioIds);
    if (ids.length === 0) return;
    try {
      const result = await deleteScenariosBulk.mutateAsync({ scenario_ids: ids });
      showToast.success(`${result.deleted} scenario${result.deleted === 1 ? '' : 's'} deleted`);
      setSelectedScenarioIds(new Set());
      setPendingBulkDelete(false);
    } catch (error) {
      handleApiError(error);
      // Modal stays open on failure — same pattern as the single-scenario
      // and folder-delete flows.
    }
  };

  const inFolderView = selectedFolder !== null;
  const activeFolder = inFolderView ? (folders.find((f) => f.id === selectedFolder) ?? null) : null;
  const activeFolderCount = activeFolder?.count ?? 0;
  const activeFolderName = activeFolder?.name ?? '';

  const actionButtons = (
    <div className="flex flex-wrap items-center justify-end gap-2">
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,text/csv"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0] ?? null;
          handleCsvPick(f);
          e.target.value = '';
        }}
      />
      <CustomButton
        type="default"
        size="sm"
        onClick={() => setOpenGenerate(true)}
        icon={<Sparkles className="size-3.5" />}
      >
        Auto-generate
      </CustomButton>
      <CustomButton
        type="default"
        size="sm"
        onClick={() => setOpenNewFolder(true)}
        icon={<FolderIcon className="size-3.5" />}
      >
        New folder
      </CustomButton>
      <CustomButton
        type="default"
        size="sm"
        onClick={() => {
          setEditing(null);
          setOpenCreate(true);
        }}
      >
        New Scenario
      </CustomButton>
      <CustomButton
        type="primary"
        size="sm"
        onClick={() => setOpenRun(true)}
        disabled={totalScenariosAllFolders === 0}
        icon={<Play className="size-3.5" />}
      >
        Run Eval
      </CustomButton>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <CustomButton
            type="default"
            size="sm"
            icon={<MoreVertical className="size-3.5" />}
            aria-label="More CSV actions"
            className="h-8 w-8 p-0"
          />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-48">
          <DropdownMenuItem onSelect={() => downloadSampleCsv()}>
            <Download className="size-3.5" />
            Sample CSV
          </DropdownMenuItem>
          <DropdownMenuItem
            disabled={uploadCsv.isPending}
            onSelect={() => fileInputRef.current?.click()}
          >
            <Upload className="size-3.5" />
            {uploadCsv.isPending ? 'Uploading…' : 'Import CSV'}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );

  const foldersPanel = (
    <SectionCard
      icon={<Gauge className="size-4" />}
      iconClassName="bg-violet-500/10 text-violet-700 dark:text-violet-400 ring-violet-500/20"
      title="LLM Evals"
      description="Score this agent's LLM output against your scenarios."
      action={actionButtons}
      bodyClassName="mt-2"
    >
      {inFolderView ? (
        <>
          <FolderBreadcrumb
            folderName={activeFolderName}
            count={activeFolderCount}
            onBack={() => setSelectedFolder(null)}
            onRename={activeFolder ? () => setEditingFolderId(activeFolder.id) : undefined}
            isEditing={!!activeFolder && editingFolderId === activeFolder.id}
            onSaveRename={saveRenameFolder}
            onCancelRename={cancelRenameFolder}
            renamePending={renameFolderMutation.isPending}
            onDelete={activeFolder ? () => setPendingDeleteFolderId(activeFolder.id) : undefined}
            // Same invariant as the folder grid: the LAST remaining folder
            // can't be deleted. Render disabled with a tooltip so users
            // still see the affordance and understand the constraint.
            canDelete={folders.length > 1}
          />
          <div className="flex flex-wrap items-center gap-2">
            <div className="min-w-[200px] flex-1">
              <SearchBar
                value={search}
                onChange={(v) => setSearch(v)}
                placeholder="Search scenarios…"
              />
            </div>
            <ScenariosSourceFilter selectedSource={filterSource} onSourceChange={setFilterSource} />
          </div>
          {selectedScenarioIds.size > 0 && (
            <div className="flex items-center justify-between gap-2 rounded-md border border-primary/40 bg-primary/5 px-3 py-2 text-[13px]">
              <span className="font-medium text-foreground">
                {selectedScenarioIds.size} scenario
                {selectedScenarioIds.size === 1 ? '' : 's'} selected
              </span>
              <div className="flex items-center gap-2">
                <CustomButton
                  type="text"
                  size="sm"
                  onClick={() => setSelectedScenarioIds(new Set())}
                >
                  Clear
                </CustomButton>
                <CustomButton
                  type="danger"
                  size="sm"
                  onClick={() => setPendingBulkDelete(true)}
                  icon={<Trash2 className="size-3.5" />}
                >
                  Delete selected
                </CustomButton>
              </div>
            </div>
          )}
          <ScenariosTable
            scenarios={scenarios}
            isLoading={scenariosQuery.isLoading}
            onEdit={(s) => {
              setEditing(s);
              setOpenCreate(true);
            }}
            onDelete={handleDelete}
            onRun={runScenario}
            isRunning={triggerRun.isPending}
            selectedIds={selectedScenarioIds}
            onToggleRow={toggleScenarioSelection}
            onToggleAll={togglePageSelection}
          />
          <LlmEvalsPagination
            page={page}
            pageSize={pageSize}
            total={scenarioCount}
            onPageChange={setPage}
            onPageSizeChange={(size) => {
              setPageSize(size);
              setPage(1);
            }}
          />
        </>
      ) : (
        <FoldersView
          folders={folders}
          isLoading={foldersQuery.isLoading}
          onOpen={(id) => setSelectedFolder(id)}
          onRunFolder={runFolder}
          onRename={(id) => setEditingFolderId(id)}
          onDelete={(id) => setPendingDeleteFolderId(id)}
          isRunning={triggerRun.isPending}
          editingFolderId={editingFolderId}
          onSaveRename={saveRenameFolder}
          onCancelRename={cancelRenameFolder}
          renamePending={renameFolderMutation.isPending}
          canDeleteAny={folders.length > 1}
        />
      )}
    </SectionCard>
  );

  const runsPanel = (
    <SectionCard
      icon={<History className="size-4" />}
      iconClassName="bg-sky-500/10 text-sky-700 dark:text-sky-400 ring-sky-500/20"
      title="Run history"
      description="Every eval batch for this agent, newest first. Click any row to inspect scored scenarios."
      action={
        <span className="text-[11px] uppercase tracking-wide text-muted-foreground">
          {runsTotal} run{runsTotal === 1 ? '' : 's'}
        </span>
      }
    >
      <RunsTable
        runs={runs}
        isLoading={runsQuery.isLoading}
        onOpen={setOpenRunId}
        onEmptyCTA={runsTotal === 0 ? () => setActiveView('folders') : undefined}
        showEmptyState={runsTotal === 0}
      />
      <LlmEvalsPagination
        page={runsPage}
        pageSize={runsPageSize}
        total={runsTotal}
        onPageChange={setRunsPage}
        onPageSizeChange={(size) => {
          setRunsPageSize(size);
          setRunsPage(1);
        }}
      />
    </SectionCard>
  );

  const tabItems: TabItem[] = [
    {
      key: 'folders',
      label: 'Folders',
      icon: <FolderIcon className="size-4" />,
      children: <div className="pt-4">{foldersPanel}</div>,
    },
    {
      key: 'runs',
      label: (
        <span className="inline-flex items-center gap-2">
          Runs
          {runsTotal > 0 && (
            <span className="inline-flex min-w-[1.25rem] items-center justify-center rounded-full bg-muted px-1.5 py-0.5 text-[10.5px] font-semibold text-muted-foreground">
              {runsTotal}
            </span>
          )}
        </span>
      ),
      icon: <History className="size-4" />,
      children: <div className="pt-4">{runsPanel}</div>,
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      <CustomTab
        activeKey={activeView}
        onTabChange={(k) => setActiveView(k as LlmEvalsView)}
        items={tabItems}
      />

      <ScenarioFormModal
        open={openCreate}
        onClose={() => setOpenCreate(false)}
        agentId={agentId}
        scenario={editing}
        folderOptions={folders}
        defaultFolderId={selectedFolder}
      />
      <RunEvalModal
        open={openRun}
        onClose={() => setOpenRun(false)}
        agentId={agentId}
        scenarios={scenarios}
        folders={folders}
        defaultFolderId={selectedFolder}
      />
      <GenerateScenariosModal
        open={openGenerate}
        onClose={() => setOpenGenerate(false)}
        agentId={agentId}
        folderOptions={folders}
        defaultFolderId={selectedFolder}
      />
      <NewFolderModal
        open={openNewFolder}
        onClose={() => {
          if (!createFolder.isPending) setOpenNewFolder(false);
        }}
        onSubmit={submitNewFolder}
        pending={createFolder.isPending}
      />
      <AgentLlmEvalResultsDrawer
        agentId={agentId}
        runId={openRunId}
        open={!!openRunId}
        onClose={() => setOpenRunId(null)}
      />
      <ConfirmDeleteModal
        open={!!pendingDelete}
        onClose={() => {
          if (!deleteScenario.isPending) setPendingDelete(null);
        }}
        onConfirm={confirmDelete}
        title="Delete scenario"
        description="This can’t be undone. Historical eval results for this scenario keep their own snapshot and are not removed."
        impact={
          pendingDelete ? (
            <p className="text-sm text-foreground">
              You’re about to delete{' '}
              <span className="font-medium">{pendingDelete.scenario_key}</span>.
            </p>
          ) : null
        }
        loading={deleteScenario.isPending}
      />
      <ConfirmDeleteModal
        open={pendingBulkDelete}
        onClose={() => {
          if (!deleteScenariosBulk.isPending) setPendingBulkDelete(false);
        }}
        onConfirm={confirmBulkDelete}
        title={`Delete ${selectedScenarioIds.size} scenario${selectedScenarioIds.size === 1 ? '' : 's'}`}
        description="This can’t be undone. Historical eval results for each deleted scenario keep their own snapshot and are not removed."
        impact={
          <p className="text-sm text-foreground">
            You’re about to delete <span className="font-medium">{selectedScenarioIds.size}</span>{' '}
            scenario
            {selectedScenarioIds.size === 1 ? '' : 's'}.
          </p>
        }
        loading={deleteScenariosBulk.isPending}
      />
      <ConfirmDeleteModal
        open={!!pendingDeleteFolderId}
        onClose={() => {
          if (!deleteFolder.isPending) setPendingDeleteFolderId(null);
        }}
        onConfirm={confirmDeleteFolder}
        title="Delete folder"
        description="This permanently deletes every scenario in this folder. Past eval-run history for the folder is preserved."
        impact={
          pendingDeleteFolderId ? (
            <div className="space-y-2 text-sm text-foreground">
              {(() => {
                const target = folders.find((f) => f.id === pendingDeleteFolderId);
                if (!target) return null;
                return (
                  <>
                    <p>
                      You’re about to delete the folder{' '}
                      <span className="font-medium">{target.name}</span> and every scenario in it.
                    </p>
                    {target.count > 0 ? (
                      <p className="text-muted-foreground">
                        <span className="font-medium text-foreground">{target.count}</span> scenario
                        {target.count === 1 ? '' : 's'} will be removed. To keep any of them, edit
                        each scenario and change its folder before deleting.
                      </p>
                    ) : (
                      <p className="text-muted-foreground">This folder is empty.</p>
                    )}
                  </>
                );
              })()}
            </div>
          ) : null
        }
        loading={deleteFolder.isPending}
      />
    </div>
  );
}

// ── Scenarios table ─────────────────────────────────────────────────────

function ScenariosTable({
  scenarios,
  isLoading,
  onEdit,
  onDelete,
  onRun,
  isRunning,
  selectedIds,
  onToggleRow,
  onToggleAll,
}: {
  scenarios: AgentLlmEvalScenario[];
  isLoading: boolean;
  onEdit: (s: AgentLlmEvalScenario) => void;
  onDelete: (s: AgentLlmEvalScenario) => void;
  // Single-scenario eval trigger. The parent owns the mutation so its
  // ``isPending`` disables every row's Run button at once — prevents a
  // second click while the first request is still in flight.
  onRun: (s: AgentLlmEvalScenario) => void;
  isRunning: boolean;
  // Bulk-selection state. ``selectedIds`` is the set of scenario ids
  // currently checked — the parent owns it so selection persists across
  // pages (a Gmail-style pattern; the header checkbox only toggles the
  // CURRENT page).
  selectedIds: Set<string>;
  onToggleRow: (id: string) => void;
  onToggleAll: () => void;
}) {
  // Native ``<input>`` doesn't expose ``indeterminate`` as a prop — set
  // it imperatively so the tri-state renders (some-but-not-all selected).
  const headerCheckboxRef = useRef<HTMLInputElement | null>(null);
  const currentPageIds = useMemo(() => scenarios.map((s) => s.id), [scenarios]);
  const currentPageSelectedCount = useMemo(
    () => currentPageIds.filter((id) => selectedIds.has(id)).length,
    [currentPageIds, selectedIds],
  );
  const allOnPageSelected = scenarios.length > 0 && currentPageSelectedCount === scenarios.length;
  const someOnPageSelected =
    currentPageSelectedCount > 0 && currentPageSelectedCount < scenarios.length;
  useEffect(() => {
    if (headerCheckboxRef.current) {
      headerCheckboxRef.current.indeterminate = someOnPageSelected;
    }
  }, [someOnPageSelected]);

  if (isLoading) {
    return (
      <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
        Loading scenarios…
      </div>
    );
  }
  if (scenarios.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
        No scenarios yet. Create one, import a CSV, or use Auto-generate.
      </div>
    );
  }
  return (
    <div className="overflow-hidden rounded-md border border-border/60">
      <table className="w-full text-sm">
        <thead className="bg-muted/40 text-[11px] uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="w-10 px-3 py-2 text-left">
              <input
                ref={headerCheckboxRef}
                type="checkbox"
                aria-label="Select all on this page"
                checked={allOnPageSelected}
                onChange={onToggleAll}
                className="cursor-pointer accent-primary"
              />
            </th>
            <th className="px-3 py-2 text-left">Scenario</th>
            <th className="px-3 py-2 text-left">Prompt</th>
            {/* Fixed-width tags + source columns so the Prompt column can
                grow into the leftover space without squeezing them to a
                sliver (which caused tag chips to wrap vertically). */}
            <th className="w-[220px] px-3 py-2 text-left">Tags</th>
            <th className="w-[100px] px-3 py-2 text-left">Source</th>
            <th className="w-[110px] px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          {scenarios.map((s) => (
            <tr
              key={s.id}
              className={cn('border-t border-border/60', selectedIds.has(s.id) && 'bg-primary/5')}
            >
              <td className="w-10 px-3 py-2 align-top">
                <input
                  type="checkbox"
                  aria-label={`Select ${s.scenario_key}`}
                  checked={selectedIds.has(s.id)}
                  onChange={() => onToggleRow(s.id)}
                  className="cursor-pointer accent-primary"
                />
              </td>
              <td className="px-3 py-2 align-top font-medium text-foreground">{s.scenario_key}</td>
              <td className="w-full px-3 py-2 align-top text-muted-foreground">
                <span
                  className="line-clamp-2 block max-w-[700px] xl:max-w-[900px]"
                  title={s.prompt}
                >
                  {s.prompt}
                </span>
              </td>
              <td className="w-[220px] px-3 py-2 align-top">
                <div className="flex flex-wrap gap-1">
                  {/* Tool-aware chip (Phase 2) — surfaces scenarios whose
                      generator pre-labeled the expected tool call so an
                      operator can see at a glance which rows will run the
                      deterministic ``tool_selection`` metric. */}
                  {s.expected_tools && s.expected_tools.length > 0 ? (
                    <span
                      title={s.expected_tools
                        .map((t) => t.name)
                        .filter(Boolean)
                        .join(', ')}
                      className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary ring-1 ring-primary/20"
                    >
                      <Wrench className="size-2.5" />
                      tool
                    </span>
                  ) : null}
                  {(s.tags ?? []).map((t) => (
                    <span
                      key={t}
                      title={t}
                      className="max-w-[200px] truncate rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </td>
              <td className="px-3 py-2 align-top">
                <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                  {s.source}
                </span>
              </td>
              <td className="px-3 py-2 align-top">
                <div className="flex items-center justify-end gap-1">
                  <button
                    type="button"
                    onClick={() => onRun(s)}
                    disabled={isRunning}
                    className="cursor-pointer rounded p-1 text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-muted-foreground"
                    aria-label={`Run ${s.scenario_key}`}
                    title="Run this scenario"
                  >
                    <Play className="size-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => onEdit(s)}
                    className="cursor-pointer rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                    aria-label="Edit scenario"
                  >
                    <Pencil className="size-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => onDelete(s)}
                    className="cursor-pointer rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                    aria-label="Delete scenario"
                  >
                    <Trash2 className="size-4" />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Scenarios filter bar ───────────────────────────────────────────────

/** Compact filter bar rendered above the scenarios table inside a folder.
 * Source is a single-select dropdown (whitelisted enum — matches backend
 * ``AgentLlmEvalScenarioSource``); tag options are derived from the
 * currently-loaded scenarios so users can filter by any tag they see.
 * A single-tag selection is enough for the JSONB "has any of" backend
 * filter — the picker is multi-select so users can broaden a scan.
 *
 * When neither filter is active AND there are no tag options, the bar
 * hides itself entirely so an empty folder doesn't get chrome it can't
 * use. */
const SCENARIO_SOURCE_OPTIONS: {
  value: AgentLlmEvalScenarioSource;
  label: string;
}[] = [
  { value: 'manual', label: 'Manual' },
  { value: 'csv', label: 'CSV import' },
  { value: 'generated', label: 'Auto-generated' },
  { value: 'fixture', label: 'Fixture' },
];

// Sentinel for the "no source filter" option. Radix Select forbids an
// empty-string value on ``<Select.Item>`` (it's reserved for clearing
// the selection to the placeholder), so we use a non-empty token and
// map it back to ``null`` at the callback boundary.
const SOURCE_FILTER_ALL_VALUE = '__all__';

/** Compact source-filter dropdown — rendered inline next to the
 * SearchBar in the folder-drill-in view so filter + search live on the
 * SAME visual row. Kept as its own component so the parent can compose
 * the row layout without inlining Radix-Select glue. */
function ScenariosSourceFilter({
  selectedSource,
  onSourceChange,
}: {
  selectedSource: AgentLlmEvalScenarioSource | null;
  onSourceChange: (next: AgentLlmEvalScenarioSource | null) => void;
}) {
  return (
    <div className="w-[180px] shrink-0">
      <SelectInput
        name="scenario_source"
        value={selectedSource ?? SOURCE_FILTER_ALL_VALUE}
        onValueChange={(v) =>
          onSourceChange(
            v === SOURCE_FILTER_ALL_VALUE || v == null ? null : (v as AgentLlmEvalScenarioSource),
          )
        }
        options={[
          { value: SOURCE_FILTER_ALL_VALUE, label: 'All sources' },
          ...SCENARIO_SOURCE_OPTIONS,
        ]}
      />
    </div>
  );
}

// ── Pagination footer ───────────────────────────────────────────────────

/** Compact pagination footer shared by every paginated list inside the LLM
 * Evals section (scenarios-in-folder + runs). Mirrors the shape used by the
 * shared ``CustomTable`` (rows-per-page selector + first/prev/current/next/
 * last controls) so pagination feels the same everywhere. Kept local to
 * this file — a 3rd caller would justify promoting it to ``@/components/shared``. */
const LLM_EVALS_PAGE_SIZE_OPTIONS = [10, 25, 50, 100] as const;

function LlmEvalsPagination({
  page,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
}: {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (p: number) => void;
  onPageSizeChange: (size: number) => void;
}) {
  if (total === 0) return null;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const currentPage = Math.min(page, totalPages);
  const firstItem = (currentPage - 1) * pageSize + 1;
  const lastItem = Math.min(currentPage * pageSize, total);
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border/60 pt-3">
      <div className="flex items-center gap-3 text-[13px] text-muted-foreground">
        <span>Rows per page</span>
        <select
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
          className="h-8 w-16 cursor-pointer rounded-lg border border-input bg-background px-2 text-[13px] text-foreground transition-colors hover:border-ring focus:outline-none focus:ring-2 focus:ring-ring/30"
        >
          {LLM_EVALS_PAGE_SIZE_OPTIONS.map((size) => (
            <option key={size} value={size}>
              {size}
            </option>
          ))}
        </select>
      </div>
      <div className="flex items-center gap-4">
        <span className="text-[13px] text-muted-foreground">
          <span className="font-medium text-foreground">
            {firstItem}
            {' - '}
            {lastItem}
          </span>
          {' of '}
          <span className="font-medium text-foreground">{total}</span>
        </span>
        <div className="flex items-center gap-1.5">
          <CustomButton
            type="text"
            size="icon-xs"
            onClick={() => onPageChange(1)}
            disabled={currentPage <= 1}
            className="rounded-lg text-muted-foreground hover:text-foreground disabled:opacity-30"
          >
            <ChevronsLeft className="size-4" />
          </CustomButton>
          <CustomButton
            type="text"
            size="icon-xs"
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage <= 1}
            className="rounded-lg text-muted-foreground hover:text-foreground disabled:opacity-30"
          >
            <ChevronLeft className="size-4" />
          </CustomButton>
          <span className="flex h-7 min-w-7 items-center justify-center rounded-lg bg-primary/10 px-2 text-xs font-medium text-primary">
            {currentPage}
          </span>
          <CustomButton
            type="text"
            size="icon-xs"
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage >= totalPages}
            className="rounded-lg text-muted-foreground hover:text-foreground disabled:opacity-30"
          >
            <ChevronRight className="size-4" />
          </CustomButton>
          <CustomButton
            type="text"
            size="icon-xs"
            onClick={() => onPageChange(totalPages)}
            disabled={currentPage >= totalPages}
            className="rounded-lg text-muted-foreground hover:text-foreground disabled:opacity-30"
          >
            <ChevronsRight className="size-4" />
          </CustomButton>
        </div>
      </div>
    </div>
  );
}

// ── Runs table ──────────────────────────────────────────────────────────

function RunsTable({
  runs,
  isLoading,
  onOpen,
  onEmptyCTA,
  showEmptyState = true,
}: {
  runs: AgentLlmEvalRunSummary[];
  isLoading: boolean;
  onOpen: (runId: string) => void;
  onEmptyCTA?: () => void;
  // ``true`` when the ENTIRE dataset is empty (not just the current page).
  // Lets a paginated caller suppress the "no runs yet" welcome state when
  // the emptiness is just an out-of-range page rather than a fresh agent.
  showEmptyState?: boolean;
}) {
  if (isLoading) {
    return (
      <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
        Loading runs…
      </div>
    );
  }
  if (runs.length === 0) {
    if (!showEmptyState) return null;
    return (
      <div className="flex flex-col items-center gap-3 rounded-md border border-dashed border-border/60 p-8 text-center">
        <History className="size-6 text-muted-foreground/60" />
        <p className="text-sm text-muted-foreground">
          No runs yet. Head to Folders and click{' '}
          <span className="font-medium text-foreground">Run Eval</span> to score this agent.
        </p>
        {onEmptyCTA && (
          <CustomButton
            type="default"
            onClick={onEmptyCTA}
            icon={<FolderIcon className="size-4" />}
          >
            Go to Folders
          </CustomButton>
        )}
      </div>
    );
  }
  return (
    <div className="overflow-hidden rounded-md border border-border/60">
      <table className="w-full text-sm">
        <thead className="bg-muted/40 text-[11px] uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="px-3 py-2 text-left">Run</th>
            <th className="px-3 py-2 text-left">Status</th>
            <th className="px-3 py-2 text-left">Started</th>
            <th className="px-3 py-2 text-left">Judge</th>
            <th className="px-3 py-2 text-left">Answer Model</th>
            <th className="px-3 py-2 text-left">Triggered</th>
            <th className="px-3 py-2 text-left">Result</th>
            <th className="px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          {runs.map((r) => {
            const summary = r.summary as Record<string, number> | Record<string, never>;
            const total = (summary.total as number) ?? 0;
            const pass = (summary.pass as number) ?? 0;
            const fail = (summary.fail as number) ?? 0;
            const partial = (summary.partial as number) ?? 0;
            const passRate = (summary.pass_rate as number) ?? 0;
            const isTerminal = RUN_TERMINAL_STATUSES.has(r.status);
            // Non-terminal rows: swap the pass/fail readout for a
            // "Scoring N of M" progress line. Also disables the drawer
            // (the drawer reads persisted rows; non-terminal runs may
            // have partial or zero rows persisted so the drawer would
            // read as empty / half-scored).
            return (
              <tr
                key={r.run_id}
                className={cn(
                  'border-t border-border/60',
                  isTerminal ? 'cursor-pointer hover:bg-muted/30' : 'cursor-default bg-muted/10',
                )}
                onClick={isTerminal ? () => onOpen(r.run_id) : undefined}
                title={isTerminal ? undefined : 'Run in progress — open once it completes'}
              >
                <td className="px-3 py-2 font-medium text-foreground">#{r.run_number}</td>
                <td className="px-3 py-2">
                  <RunStatusChip status={r.status} />
                </td>
                <td className="px-3 py-2 text-muted-foreground">
                  {r.started_at ? formatDate(r.started_at) : '—'}
                </td>
                <td className="px-3 py-2 text-muted-foreground">{r.judge_model ?? '—'}</td>
                <td className="px-3 py-2 text-muted-foreground">
                  {r.llm_model ?? '—'}
                  {r.llm_provider && (
                    <span className="ml-1 text-[11px] text-muted-foreground/70">
                      · {r.llm_provider}
                    </span>
                  )}
                </td>
                <td className="px-3 py-2 text-muted-foreground">{r.triggered_by}</td>
                <td className="px-3 py-2">
                  {isTerminal ? (
                    <div className="flex items-center gap-2">
                      <span className="tabular-nums text-foreground">
                        <span className="text-emerald-600">{pass}</span>
                        {partial > 0 && (
                          <>
                            {' / '}
                            <span className="text-amber-600">{partial}</span>
                          </>
                        )}
                        {fail > 0 && (
                          <>
                            {' / '}
                            <span className="text-destructive">{fail}</span>
                          </>
                        )}
                        <span className="text-muted-foreground"> of {total}</span>
                      </span>
                      <span className="text-[11px] tabular-nums text-muted-foreground">
                        {Math.round(passRate * 100)}%
                      </span>
                    </div>
                  ) : (
                    <span className="text-[12px] tabular-nums text-muted-foreground">
                      Scoring <span className="font-medium text-foreground">{r.scored_count}</span>
                      {' of '}
                      <span className="font-medium text-foreground">
                        {r.total_scenarios || '—'}
                      </span>
                    </span>
                  )}
                </td>
                <td className="px-3 py-2 text-right text-muted-foreground">
                  {isTerminal ? (
                    <ChevronRight className="ml-auto size-4" />
                  ) : (
                    <span className="text-[10px] uppercase tracking-wide text-muted-foreground/70">
                      In progress
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Folders view (default) + drilled-in header ──────────────────────────

/** Default view — a grid of folder cards. Clicking a card drills into
 * that folder's scenarios (see ``FolderBreadcrumb``). Every scenario
 * belongs to a real folder — there is no Uncategorized bucket. Empty
 * folders survive after their last scenario is deleted so they still
 * render as a card. */
function FoldersView({
  folders,
  isLoading,
  onOpen,
  onRunFolder,
  onRename,
  onDelete,
  isRunning,
  editingFolderId,
  onSaveRename,
  onCancelRename,
  renamePending,
  canDeleteAny,
}: {
  folders: AgentLlmEvalFolder[];
  isLoading: boolean;
  onOpen: (folderId: string) => void;
  onRunFolder: (folderId: string) => void;
  onRename: (folderId: string) => void;
  onDelete: (folderId: string) => void;
  isRunning: boolean;
  // Inline-rename plumbing. ``editingFolderId`` is the id of the folder
  // currently in edit mode (only one at a time). Cards compare their own
  // id against it to decide whether to render the editor.
  editingFolderId: string | null;
  onSaveRename: (next: string) => void;
  onCancelRename: () => void;
  renamePending: boolean;
  // Every agent must always have at least one folder — the delete affordance
  // is hidden on the last folder to prevent the "no folders" empty state.
  canDeleteAny: boolean;
}) {
  if (isLoading) {
    return (
      <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
        Loading folders…
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      {folders.length === 0 ? (
        <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
          No folders yet. Click <span className="font-medium">New folder</span> to create one.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {folders.map((f) => (
            <FolderCard
              key={f.id}
              name={f.name}
              count={f.count}
              canRename
              onOpen={() => onOpen(f.id)}
              onRun={() => onRunFolder(f.id)}
              onRename={() => onRename(f.id)}
              // Always show the Delete affordance so users can see the
              // feature exists — the LAST folder for an agent renders it
              // disabled with an explanatory tooltip (backend enforces
              // the same invariant via ``FOLDER_NOT_DELETABLE``).
              onDelete={() => onDelete(f.id)}
              canDelete={canDeleteAny}
              isRunning={isRunning}
              isEditing={editingFolderId === f.id}
              onSaveRename={onSaveRename}
              onCancelRename={onCancelRename}
              renamePending={renamePending}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/** Inline single-field editor for a folder name. Replaces the old
 * "rename folder" modal — clicking Rename on a folder card / breadcrumb
 * swaps the name span for this editor in place, so the user never leaves
 * the folders grid.
 *
 * ✓ (or Enter) commits, ✕ (or Escape) cancels. A blank / unchanged
 * value silently cancels — matches how contact-directory rename works
 * elsewhere in the app. The parent owns the mutation and passes
 * ``pending`` to disable the buttons + input while the save is in flight.
 *
 * Rendered inside interactive containers (a ``<button>`` card, a
 * clickable breadcrumb row), so click / keydown handlers stop propagation
 * to prevent the drill-in / focus-shift from also firing. */
function InlineFolderNameEditor({
  initialValue,
  onSave,
  onCancel,
  pending = false,
  size = 'sm',
}: {
  initialValue: string;
  onSave: (next: string) => void;
  onCancel: () => void;
  pending?: boolean;
  // ``sm`` = folder-card scale, ``md`` = breadcrumb scale. Tuned so the
  // editor visually replaces the corresponding name span without shifting
  // the surrounding layout.
  size?: 'sm' | 'md';
}) {
  const [value, setValue] = useState(initialValue);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    // Autofocus + select-all so the user can immediately overwrite or
    // start typing — matches native inline-rename UX (Finder, Drive).
    if (inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, []);

  useEffect(() => {
    // Re-sync when the underlying folder name changes externally
    // (concurrent rename by another user + a folders-query refetch).
    // Without this the editor keeps showing the stale name and ✓ would
    // try to rename a folder that no longer exists.
    setValue(initialValue);
  }, [initialValue]);

  const commit = () => {
    if (pending) return;
    const trimmed = value.trim();
    // Blank or unchanged → silent cancel (no toast, no request).
    if (!trimmed || trimmed === initialValue) {
      onCancel();
      return;
    }
    onSave(trimmed);
  };

  return (
    <div
      className="flex items-center gap-1"
      onClick={(e) => e.stopPropagation()}
      onKeyDown={(e) => {
        // Prevent the enclosing card / breadcrumb from picking up
        // Enter/Space when the input has focus.
        e.stopPropagation();
      }}
      role="presentation"
    >
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            commit();
          } else if (e.key === 'Escape') {
            e.preventDefault();
            onCancel();
          }
        }}
        disabled={pending}
        maxLength={120}
        className={cn(
          'min-w-0 flex-1 rounded-md border border-input bg-background px-2 font-semibold text-foreground outline-none transition-colors focus:border-ring focus:ring-2 focus:ring-ring/30 disabled:cursor-not-allowed disabled:opacity-60',
          size === 'sm' ? 'h-7 text-[13px]' : 'h-8 text-[14px]',
        )}
        aria-label="Folder name"
      />
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          commit();
        }}
        disabled={pending}
        aria-label="Save folder name"
        title="Save"
        className={cn(
          'inline-flex shrink-0 cursor-pointer items-center justify-center rounded-md text-emerald-700 transition-colors hover:bg-emerald-500/10 disabled:cursor-not-allowed disabled:opacity-50 dark:text-emerald-400',
          size === 'sm' ? 'size-7' : 'size-8',
        )}
      >
        {pending ? <Loader2 className="size-3.5 animate-spin" /> : <Check className="size-3.5" />}
      </button>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onCancel();
        }}
        disabled={pending}
        aria-label="Cancel rename"
        title="Cancel"
        className={cn(
          'inline-flex shrink-0 cursor-pointer items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:cursor-not-allowed disabled:opacity-50',
          size === 'sm' ? 'size-7' : 'size-8',
        )}
      >
        <X className="size-3.5" />
      </button>
    </div>
  );
}

/** One folder tile — clickable to open, with quick Run + Rename actions
 * always visible at the bottom (muted → foreground on hover). The whole
 * card is a ``<button>``; nested actions use ``<span role="button">`` +
 * ``e.stopPropagation()`` (invalid to nest ``<button>`` inside a button).
 * The delete affordance always renders so users see the feature exists;
 * ``canDelete=false`` renders it disabled with a tooltip (the agent's
 * LAST folder can't be deleted — invariant enforced by the backend too). */
function FolderCard({
  name,
  count,
  canRename,
  onOpen,
  onRun,
  onRename,
  onDelete,
  canDelete = true,
  isRunning,
  isEditing = false,
  onSaveRename,
  onCancelRename,
  renamePending = false,
}: {
  name: string;
  count: number;
  canRename: boolean;
  onOpen: () => void;
  onRun: () => void;
  onRename?: () => void;
  // Always provided by ``FoldersView`` — see ``canDelete`` for the gate.
  onDelete?: () => void;
  // ``false`` for the agent's last remaining folder. Renders the Delete
  // button disabled with a tooltip explaining the invariant.
  canDelete?: boolean;
  isRunning: boolean;
  // Inline-edit state. When ``isEditing`` is true, the name span is
  // swapped for ``InlineFolderNameEditor`` and the drill-in click is
  // suppressed so a click inside the input doesn't also open the folder.
  isEditing?: boolean;
  onSaveRename?: (next: string) => void;
  onCancelRename?: () => void;
  renamePending?: boolean;
}) {
  const isMuted = false;
  const runDisabled = isRunning || count === 0;
  // The whole card is normally a ``<button>`` so the entire tile is
  // clickable. During inline edit we swap to a ``<div>`` because native
  // HTML forbids a ``<button>`` inside a ``<button>`` and the editor's
  // ✓/✕ / input are interactive controls.
  const Container = isEditing ? 'div' : 'button';
  return (
    <Container
      type={isEditing ? undefined : ('button' as const)}
      onClick={isEditing ? undefined : onOpen}
      className={cn(
        'group relative flex h-full flex-col gap-4 rounded-xl border border-border/60 p-4 text-left',
        'transition-all duration-150',
        !isEditing &&
          'hover:-translate-y-0.5 hover:border-border hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1',
        isEditing && 'ring-2 ring-ring/40',
        isMuted ? 'bg-muted/30' : 'bg-card',
      )}
      aria-label={isEditing ? `Renaming folder ${name}` : `Open folder ${name}`}
    >
      {/* Top row: folder icon + name. Icon is prominent so the "folder"
          metaphor is instantly readable; the small chevron on the right
          signals "click to drill in" (opacity picks up on hover). */}
      <div className="flex items-start gap-3">
        <div
          className={cn(
            'flex size-10 shrink-0 items-center justify-center rounded-lg ring-1',
            isMuted
              ? 'bg-muted text-muted-foreground ring-border'
              : 'bg-violet-500/10 text-violet-700 ring-violet-500/20 dark:text-violet-400',
          )}
        >
          <FolderIcon className="size-5" />
        </div>
        <div className="min-w-0 flex-1 pt-0.5">
          {isEditing && onSaveRename && onCancelRename ? (
            <InlineFolderNameEditor
              initialValue={name}
              onSave={onSaveRename}
              onCancel={onCancelRename}
              pending={renamePending}
              size="sm"
            />
          ) : (
            <div
              className="truncate text-[14px] font-semibold leading-tight text-foreground"
              title={name}
            >
              {name}
            </div>
          )}
          <div className="mt-1 inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-[10.5px] font-medium text-muted-foreground">
            {count} scenario{count === 1 ? '' : 's'}
          </div>
        </div>
        {!isEditing && (
          <ChevronRight
            className={cn(
              'mt-1 size-4 shrink-0 text-muted-foreground/40 transition-all',
              'group-hover:translate-x-0.5 group-hover:text-muted-foreground',
            )}
          />
        )}
      </div>

      {/* Bottom action row — always visible, muted by default so the card
          reads clean, brightens on card hover so users know they're
          interactive. Divider gives visual separation without extra chrome.
          Actions are hidden during inline rename so the editor gets full
          focus (the ✓/✕ inside the editor are the only relevant actions). */}
      {!isEditing && (
        <div className="mt-auto flex items-center gap-1 border-t border-border/50 pt-3">
          {canRename && onRename && (
            <FolderCardAction
              icon={<Pencil className="size-3.5" />}
              label="Rename"
              onActivate={onRename}
              title={`Rename ${name}`}
            />
          )}
          {onDelete && (
            <FolderCardAction
              icon={<Trash2 className="size-3.5" />}
              label="Delete"
              onActivate={onDelete}
              emphasis="danger"
              disabled={!canDelete}
              title={
                canDelete
                  ? `Delete folder ${name}`
                  : 'Every agent must have at least one folder — create another folder before deleting this one.'
              }
            />
          )}
          <FolderCardAction
            icon={<Play className="size-3.5" />}
            label="Run folder"
            onActivate={onRun}
            disabled={runDisabled}
            title={count === 0 ? 'Folder is empty' : `Run ${name}`}
            emphasis="primary"
            className="ml-auto"
          />
        </div>
      )}
    </Container>
  );
}

/** Nested pseudo-button inside a ``FolderCard``. Kept as ``<span role="button">``
 * because HTML doesn't allow nesting ``<button>`` inside ``<button>``, and the
 * card itself already owns the drill-in click. Handles Enter/Space, disabled
 * state, and stops propagation so the card's drill-in doesn't also fire. */
function FolderCardAction({
  icon,
  label,
  onActivate,
  disabled = false,
  title,
  emphasis = 'default',
  className,
}: {
  icon: React.ReactNode;
  label: string;
  onActivate: () => void;
  disabled?: boolean;
  title?: string;
  // ``danger`` matches the destructive-action visual grammar used on the
  // scenarios row (red hover) — reserved for Delete so users can't
  // mistake it for a benign action.
  emphasis?: 'default' | 'primary' | 'danger';
  className?: string;
}) {
  return (
    <span
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-disabled={disabled}
      onClick={(e) => {
        e.stopPropagation();
        if (!disabled) onActivate();
      }}
      onKeyDown={(e) => {
        if ((e.key === 'Enter' || e.key === ' ') && !disabled) {
          e.preventDefault();
          e.stopPropagation();
          onActivate();
        }
      }}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[11.5px] font-medium transition-colors',
        disabled
          ? 'cursor-not-allowed text-muted-foreground/40'
          : emphasis === 'primary'
            ? 'cursor-pointer text-foreground hover:bg-primary hover:text-primary-foreground'
            : emphasis === 'danger'
              ? 'cursor-pointer text-muted-foreground hover:bg-destructive/10 hover:text-destructive'
              : 'cursor-pointer text-muted-foreground hover:bg-muted hover:text-foreground',
        className,
      )}
      title={title}
      aria-label={label}
    >
      {icon}
      <span>{label}</span>
    </span>
  );
}

/** Compact breadcrumb shown when the user has drilled into a folder — just
 * enough to say "you're inside this folder": ``← All folders / <name> · N
 * scenarios``. Rename stays available as a small icon-only affordance next
 * to the name. Per-folder run is triggered from the folder card in the grid
 * view; the global "Run Eval" button in the header covers running from
 * inside a folder. */
function FolderBreadcrumb({
  folderName,
  count,
  onBack,
  onRename,
  isEditing = false,
  onSaveRename,
  onCancelRename,
  renamePending = false,
  onDelete,
  canDelete = true,
}: {
  folderName: string;
  count: number;
  onBack: () => void;
  onRename?: () => void;
  // Inline-rename state — mirrors ``FolderCard``. When ``isEditing`` is
  // true the folder-name span is swapped for ``InlineFolderNameEditor``.
  isEditing?: boolean;
  onSaveRename?: (next: string) => void;
  onCancelRename?: () => void;
  renamePending?: boolean;
  onDelete?: () => void;
  // ``false`` for the agent's last remaining folder — the button still
  // renders (so the affordance is discoverable) but is disabled with a
  // tooltip explaining the invariant.
  canDelete?: boolean;
}) {
  const displayName = folderName;
  return (
    <div className="flex flex-wrap items-center gap-2 text-[12.5px]">
      <button
        type="button"
        onClick={onBack}
        className="inline-flex cursor-pointer items-center gap-1 font-medium text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="size-3.5" />
        All folders
      </button>
      <ChevronRight className="size-3.5 text-muted-foreground/60" />
      <FolderIcon className="size-3.5 text-muted-foreground" />
      {isEditing && onSaveRename && onCancelRename ? (
        <InlineFolderNameEditor
          initialValue={displayName}
          onSave={onSaveRename}
          onCancel={onCancelRename}
          pending={renamePending}
          size="md"
        />
      ) : (
        <>
          <span
            className="max-w-[240px] truncate font-semibold text-foreground"
            title={displayName}
          >
            {displayName}
          </span>
          <span className="text-muted-foreground">
            · {count} scenario{count === 1 ? '' : 's'}
          </span>
          {onRename && (
            <button
              type="button"
              onClick={onRename}
              aria-label={`Rename ${displayName}`}
              title="Rename folder"
              className="ml-1 inline-flex cursor-pointer items-center justify-center rounded p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <Pencil className="size-3.5" />
            </button>
          )}
          {onDelete && (
            <button
              type="button"
              onClick={canDelete ? onDelete : undefined}
              disabled={!canDelete}
              aria-label={`Delete folder ${displayName}`}
              title={
                canDelete
                  ? 'Delete folder'
                  : 'Every agent must have at least one folder — create another folder before deleting this one.'
              }
              className={cn(
                'inline-flex items-center justify-center rounded p-1 transition-colors',
                canDelete
                  ? 'cursor-pointer text-muted-foreground hover:bg-destructive/10 hover:text-destructive'
                  : 'cursor-not-allowed text-muted-foreground/40',
              )}
            >
              <Trash2 className="size-3.5" />
            </button>
          )}
        </>
      )}
    </div>
  );
}

/** Shared folder picker for the create/edit and generate modals.
 *
 * Two states in one component: a dropdown of existing folders (with a
 * "+ Create new folder…" affordance) OR a text input when the user chose
 * to create a new one. Values are folder ids — when in create mode the
 * caller receives ``__new_folder__`` and the ``pendingName`` prop so it
 * can create-then-use the returned id at submit time. */
function FolderPicker({
  folders,
  value,
  onChange,
  newFolderName,
  onNewFolderNameChange,
  label = 'Folder',
}: {
  folders: AgentLlmEvalFolder[];
  // A folder id, or the sentinel ``NEW_FOLDER_OPTION_VALUE`` while the
  // user is typing a new-folder name.
  value: string;
  onChange: (v: string) => void;
  // New-folder text state — held on the parent so the submit handler can
  // read the typed name at commit time.
  newFolderName: string;
  onNewFolderNameChange: (name: string) => void;
  label?: string;
}) {
  const options = useMemo(
    () => [
      ...folders.map((f) => ({ value: f.id, label: f.name })),
      { value: NEW_FOLDER_OPTION_VALUE, label: '+ Create new folder…' },
    ],
    [folders],
  );

  const handleSelectChange = (v: string | null) => {
    if (!v) return;
    onChange(v);
  };

  if (value === NEW_FOLDER_OPTION_VALUE) {
    return (
      <div className="flex flex-col gap-1">
        <TextInput
          name="folder_new"
          label={label}
          placeholder="New folder name"
          value={newFolderName}
          onChange={(e) => onNewFolderNameChange(e.target.value)}
        />
        <button
          type="button"
          className="self-start text-[11px] text-muted-foreground underline underline-offset-2 hover:text-foreground"
          onClick={() => {
            onChange(folders[0]?.id ?? '');
            onNewFolderNameChange('');
          }}
        >
          Pick an existing folder instead
        </button>
      </div>
    );
  }

  // ``value`` is passed through as-is (no ``|| folders[0]?.id`` fallback)
  // so the SelectInput's rendered value ALWAYS matches parent state — a
  // silent divergence would land scenarios in an unintended folder. The
  // parent's own useEffect backfills a valid id once folders load.
  return (
    <SelectInput
      name="folder_id"
      label={label}
      value={value}
      onValueChange={handleSelectChange}
      options={options}
    />
  );
}

// ── Scenario create/edit modal ──────────────────────────────────────────

function ScenarioFormModal({
  open,
  onClose,
  agentId,
  scenario,
  folderOptions,
  defaultFolderId,
}: {
  open: boolean;
  onClose: () => void;
  agentId: string;
  scenario: AgentLlmEvalScenario | null;
  folderOptions: AgentLlmEvalFolder[];
  defaultFolderId: string | null;
}) {
  const isEdit = !!scenario;
  const create = useCreateAgentLlmEvalScenario(agentId);
  const update = useUpdateAgentLlmEvalScenario(agentId);
  const createFolder = useCreateAgentLlmEvalFolder(agentId);

  const [key, setKey] = useState('');
  const [prompt, setPrompt] = useState('');
  const [expected, setExpected] = useState('');
  const [persona, setPersona] = useState('');
  const [instruction, setInstruction] = useState('');
  const [tags, setTags] = useState('');
  // Folder id, or the ``NEW_FOLDER_OPTION_VALUE`` sentinel while creating.
  const [folderId, setFolderId] = useState('');
  const [newFolderName, setNewFolderName] = useState('');

  // Initialise once when the modal opens or the target scenario changes.
  // Deliberately omit ``folderOptions`` from deps — the folders query has
  // ``staleTime: 0`` so its data reference changes on every background
  // refetch. Including it here would silently reset the user's mid-edit
  // folder pick every time the query refetches.
  useEffect(() => {
    if (!open) return;
    setKey(scenario?.scenario_key ?? '');
    setPrompt(scenario?.prompt ?? '');
    setExpected(scenario?.expected_answer ?? '');
    setPersona(scenario?.persona_criteria ?? '');
    setInstruction(scenario?.instruction_criteria ?? '');
    setTags((scenario?.tags ?? []).join(', '));
    setFolderId(scenario?.folder_id ?? defaultFolderId ?? '');
    setNewFolderName('');
  }, [open, scenario, defaultFolderId]);

  // Defensive backfill: if the modal opened before the folders query
  // resolved, folderId is '' — pick the first folder once folders arrive
  // so the SelectInput's rendered value matches state (fixes silent
  // display/state divergence in ``FolderPicker``).
  useEffect(() => {
    if (!open || folderId || folderId === NEW_FOLDER_OPTION_VALUE) return;
    if (folderOptions.length === 0) return;
    setFolderId(folderOptions[0].id);
  }, [open, folderId, folderOptions]);

  const submit = async () => {
    const parsedTags = tags
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);
    try {
      // Resolve the folder id — either an existing selection or a
      // just-created folder from the "+ Create new folder…" affordance.
      let resolvedFolderId = folderId;
      if (folderId === NEW_FOLDER_OPTION_VALUE) {
        const trimmed = newFolderName.trim();
        if (!trimmed) {
          showToast.error('Folder name is required');
          return;
        }
        const created = await createFolder.mutateAsync({ name: trimmed });
        resolvedFolderId = created.id;
      }

      if (isEdit && scenario) {
        // Only send fields the user actually changed — otherwise a
        // concurrent edit (another tab / user) gets silently reverted.
        // Tags need a stringified-set compare because the DB stores them
        // as a JSONB array whose order we shouldn't rely on for equality.
        const originalTags = (scenario.tags ?? []).slice().sort().join(',');
        const nextTags = parsedTags.slice().sort().join(',');
        const patch: ScenarioPatch = {
          scenario_key: key !== scenario.scenario_key ? key : undefined,
          prompt: prompt !== scenario.prompt ? prompt : undefined,
          expected_answer: expected !== (scenario.expected_answer ?? '') ? expected : undefined,
          persona_criteria: persona !== (scenario.persona_criteria ?? '') ? persona : undefined,
          instruction_criteria:
            instruction !== (scenario.instruction_criteria ?? '') ? instruction : undefined,
          tags: nextTags !== originalTags ? parsedTags : undefined,
          folder_id:
            resolvedFolderId && resolvedFolderId !== scenario.folder_id
              ? resolvedFolderId
              : undefined,
        };
        await update.mutateAsync({ scenarioId: scenario.id, patch });
        showToast.success('Scenario updated');
      } else {
        const input: ScenarioInput = {
          scenario_key: key,
          prompt,
          expected_answer: expected || null,
          persona_criteria: persona || null,
          instruction_criteria: instruction || null,
          tags: parsedTags.length ? parsedTags : null,
          folder_id: resolvedFolderId || null,
        };
        await create.mutateAsync(input);
        showToast.success('Scenario created');
      }
      onClose();
    } catch (error) {
      handleApiError(error);
    }
  };

  const pending = create.isPending || update.isPending || createFolder.isPending;

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Edit scenario' : 'New scenario'}
      description="A prompt + optional expected answer or judging criteria."
      width="max-w-2xl"
      footer={
        <div className="flex justify-end gap-2">
          <CustomButton type="default" onClick={onClose} disabled={pending}>
            Cancel
          </CustomButton>
          <CustomButton
            type="primary"
            onClick={submit}
            disabled={pending || !key.trim() || !prompt.trim()}
            loading={pending}
          >
            {isEdit ? 'Save changes' : 'Create scenario'}
          </CustomButton>
        </div>
      }
    >
      <div className="flex flex-col gap-3">
        <TextInput
          name="scenario_key"
          label="Scenario key"
          placeholder="e.g. simple_room_booking"
          value={key}
          onChange={(e) => setKey(e.target.value)}
          isRequired
        />
        <TextAreaField
          name="prompt"
          label="Prompt"
          placeholder="The user message the agent should respond to"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={4}
          isRequired
        />
        <TextAreaField
          name="expected_answer"
          label="Expected answer (optional)"
          placeholder="Used by the correctness metric"
          value={expected}
          onChange={(e) => setExpected(e.target.value)}
          rows={3}
        />
        <TextAreaField
          name="persona_criteria"
          label="Persona criteria (optional)"
          placeholder="How the agent should sound (empathetic, professional, etc.)"
          value={persona}
          onChange={(e) => setPersona(e.target.value)}
          rows={2}
        />
        <TextAreaField
          name="instruction_criteria"
          label="Instruction criteria (optional)"
          placeholder="What the agent must / must not do"
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          rows={2}
        />
        <TextInput
          name="tags"
          label="Tags"
          placeholder="Comma-separated (e.g. booking, happy_path)"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
        />
        <FolderPicker
          folders={folderOptions}
          value={folderId}
          onChange={setFolderId}
          newFolderName={newFolderName}
          onNewFolderNameChange={setNewFolderName}
        />
      </div>
    </CustomModal>
  );
}

// ── Run eval modal ──────────────────────────────────────────────────────

function RunEvalModal({
  open,
  onClose,
  agentId,
  scenarios,
  folders,
  defaultFolderId,
}: {
  open: boolean;
  onClose: () => void;
  agentId: string;
  scenarios: AgentLlmEvalScenario[];
  folders: AgentLlmEvalFolder[];
  defaultFolderId: FolderScope;
}) {
  const trigger = useTriggerAgentLlmEvalRun(agentId);
  const [judge, setJudge] = useState('');
  const [scope, setScope] = useState<'all' | 'tags' | 'folders'>('all');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  // Each entry: a folder id. Chip-toggle multi-select mirroring the tag picker.
  const [selectedFolderIds, setSelectedFolderIds] = useState<string[]>([]);

  const tagOptions = useMemo(() => {
    const all = new Set<string>();
    for (const s of scenarios) for (const t of s.tags ?? []) all.add(t);
    return Array.from(all)
      .sort()
      .map((t) => ({ value: t, label: t }));
  }, [scenarios]);

  const folderOptions = useMemo(
    () =>
      folders.map((f) => ({
        value: f.id,
        label: f.name,
        count: f.count,
      })),
    [folders],
  );

  useEffect(() => {
    if (!open) {
      setJudge('');
      setScope('all');
      setSelectedTags([]);
      setSelectedFolderIds([]);
      return;
    }
    // If a folder was open when the user opened the modal, pre-seed the
    // multi-select with that one folder — saves them re-picking. They can
    // then check additional folders before running.
    if (defaultFolderId !== null) {
      setScope('folders');
      setSelectedFolderIds([defaultFolderId]);
    }
  }, [open, defaultFolderId]);

  const selectedFoldersCount = useMemo(() => {
    if (!selectedFolderIds.length) return 0;
    return folderOptions
      .filter((o) => selectedFolderIds.includes(o.value))
      .reduce((n, o) => n + o.count, 0);
  }, [selectedFolderIds, folderOptions]);

  const toggleFolder = (value: string) => {
    setSelectedFolderIds((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value],
    );
  };

  const canSubmit =
    scope !== 'folders' || (selectedFolderIds.length > 0 && selectedFoldersCount > 0);

  const submit = async () => {
    try {
      await trigger.mutateAsync({
        judge_model: judge.trim() || undefined,
        tags: scope === 'tags' && selectedTags.length ? selectedTags : undefined,
        // Send the plural `folder_ids` field on multi-select. Backend
        // prefers `folder_ids` when both are provided.
        folder_ids: scope === 'folders' && selectedFolderIds.length ? selectedFolderIds : undefined,
      });
      showToast.success(
        'Evaluation started',
        'Your scenarios are running now. Open the Runs tab in a moment to see the results.',
      );
      onClose();
    } catch (error) {
      handleApiError(error);
    }
  };

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title="Run LLM eval"
      description="Enqueues an async job. Refresh in a few seconds to see the run."
      width="max-w-lg"
      footer={
        <div className="flex justify-end gap-2">
          <CustomButton type="default" onClick={onClose} disabled={trigger.isPending}>
            Cancel
          </CustomButton>
          <CustomButton
            type="primary"
            onClick={submit}
            loading={trigger.isPending}
            disabled={!canSubmit}
          >
            Run eval
          </CustomButton>
        </div>
      }
    >
      <div className="flex flex-col gap-3">
        <SelectInput
          name="scope"
          label="Scope"
          value={scope}
          onValueChange={(v) => setScope((v as 'all' | 'tags' | 'folders') ?? 'all')}
          options={[
            { value: 'all', label: `Every scenario (${scenarios.length})` },
            { value: 'folders', label: 'Filter by folder(s)' },
            { value: 'tags', label: 'Filter by tag' },
          ]}
        />
        {scope === 'folders' && folderOptions.length > 0 && (
          <div className="flex flex-col gap-2">
            <div className="flex flex-wrap gap-2">
              {folderOptions.map((f) => {
                const active = selectedFolderIds.includes(f.value);
                const isEmpty = f.count === 0;
                return (
                  <button
                    type="button"
                    key={f.value}
                    onClick={() => toggleFolder(f.value)}
                    disabled={isEmpty}
                    className={cn(
                      'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium ring-1 transition-colors',
                      active
                        ? 'bg-primary text-primary-foreground ring-primary'
                        : 'bg-muted text-muted-foreground ring-border hover:bg-muted/80',
                      isEmpty && 'cursor-not-allowed opacity-50',
                    )}
                    aria-pressed={active}
                    title={isEmpty ? 'Folder is empty' : `${f.label} (${f.count})`}
                  >
                    <FolderIcon className="size-3" />
                    <span>{f.label}</span>
                    <span
                      className={cn(
                        'inline-flex min-w-[1rem] items-center justify-center rounded-full px-1 text-[10px] font-semibold',
                        active
                          ? 'bg-primary-foreground/20 text-primary-foreground'
                          : 'bg-card text-muted-foreground',
                      )}
                    >
                      {f.count}
                    </span>
                  </button>
                );
              })}
            </div>
            <p className="text-[11px] text-muted-foreground">
              {selectedFolderIds.length === 0
                ? 'Pick one or more folders.'
                : `${selectedFoldersCount} scenario${selectedFoldersCount === 1 ? '' : 's'} across ${selectedFolderIds.length} folder${selectedFolderIds.length === 1 ? '' : 's'} will run.`}
            </p>
          </div>
        )}
        {scope === 'tags' && tagOptions.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {tagOptions.map((t) => {
              const active = selectedTags.includes(t.value);
              return (
                <button
                  type="button"
                  key={t.value}
                  onClick={() =>
                    setSelectedTags((prev) =>
                      active ? prev.filter((x) => x !== t.value) : [...prev, t.value],
                    )
                  }
                  className={cn(
                    'rounded-full px-2.5 py-1 text-[11px] font-medium ring-1',
                    active
                      ? 'bg-primary text-primary-foreground ring-primary'
                      : 'bg-muted text-muted-foreground ring-border hover:bg-muted/80',
                  )}
                >
                  {t.label}
                </button>
              );
            })}
          </div>
        )}
        <TextInput
          name="judge_model"
          label="Judge model override (optional)"
          placeholder="Leave blank to use the org default"
          value={judge}
          onChange={(e) => setJudge(e.target.value)}
        />
      </div>
    </CustomModal>
  );
}

// ── Generate scenarios modal ────────────────────────────────────────────

// Bound + default match the backend's ``_MAX_COUNT`` in
// ``scenario_generation/strategies/llm.py`` — the server clamps anyway, but
// mirroring the bound here saves a round-trip on a mistyped input.
const GENERATE_DEFAULT_COUNT = 10;
const GENERATE_MAX_COUNT = 50;

function GenerateScenariosModal({
  open,
  onClose,
  agentId,
  folderOptions,
  defaultFolderId,
}: {
  open: boolean;
  onClose: () => void;
  agentId: string;
  folderOptions: AgentLlmEvalFolder[];
  defaultFolderId: string | null;
}) {
  // Two-step flow: dry-run generate → preview table with per-row
  // checkboxes → user confirms → bulk-create only the selected items with
  // ``source='generated'`` so the source badge in the scenarios table
  // still reflects reality. The bulk endpoint is the SAME code path a
  // manual bulk create uses (duplicate keys 409 the whole batch), which
  // keeps the scenario-write invariants in one place.
  const generate = useGenerateAgentLlmEvalScenarios(agentId);
  const persist = useCreateAgentLlmEvalScenariosBulk(agentId);
  const createFolder = useCreateAgentLlmEvalFolder(agentId);
  const [count, setCount] = useState(String(GENERATE_DEFAULT_COUNT));
  const [folderId, setFolderId] = useState('');
  const [newFolderName, setNewFolderName] = useState('');
  // Preview state — ``null`` = the form is showing; a non-null array
  // = the preview table is showing. Kept as separate state (not derived
  // from ``generate.data``) so switching from preview back to form
  // (Regenerate) doesn't tear down the visible table before we're ready.
  const [preview, setPreview] = useState<GeneratedScenario[] | null>(null);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!open) {
      // Reset every piece of state on close so a re-open starts fresh
      // (avoids resurrecting a stale preview from a previous session).
      setCount(String(GENERATE_DEFAULT_COUNT));
      setFolderId('');
      setNewFolderName('');
      setPreview(null);
      setSelectedKeys(new Set());
      return;
    }
    setFolderId(defaultFolderId ?? '');
    setNewFolderName('');
  }, [open, defaultFolderId]);

  // Backfill folderId once folders load — see the matching effect on
  // ``ScenarioFormModal`` for the rationale.
  useEffect(() => {
    if (!open || folderId || folderId === NEW_FOLDER_OPTION_VALUE) return;
    if (folderOptions.length === 0) return;
    setFolderId(folderOptions[0].id);
  }, [open, folderId, folderOptions]);

  const resolveFolderIdOrCreate = async (): Promise<string | null> => {
    if (folderId === NEW_FOLDER_OPTION_VALUE) {
      const trimmed = newFolderName.trim();
      if (!trimmed) {
        showToast.error('Folder name is required');
        return null;
      }
      const created = await createFolder.mutateAsync({ name: trimmed });
      setFolderId(created.id);
      return created.id;
    }
    return folderId || null;
  };

  const runGenerate = async () => {
    const parsedCount = Math.max(
      1,
      Math.min(GENERATE_MAX_COUNT, Number(count) || GENERATE_DEFAULT_COUNT),
    );
    try {
      const result = await generate.mutateAsync({
        strategy: 'llm',
        count: parsedCount,
        // Preview only — nothing is written yet. The subsequent
        // ``persist`` mutation writes the user's selection with
        // ``source='generated'``.
        dry_run: true,
      });
      if (result.generated.length === 0) {
        showToast.info(
          'Auto-generate',
          result.note ??
            'The generator returned no usable scenarios. Try again, or tweak the agent’s system prompt.',
        );
        return;
      }
      setPreview(result.generated);
      // Default to every row selected — the common case is "accept all".
      setSelectedKeys(new Set(result.generated.map((s) => s.scenario_key)));
    } catch (error) {
      handleApiError(error);
    }
  };

  const savePreview = async () => {
    if (!preview) return;
    const chosen = preview.filter((s) => selectedKeys.has(s.scenario_key));
    if (chosen.length === 0) return;
    try {
      const resolvedFolderId = await resolveFolderIdOrCreate();
      const result = await persist.mutateAsync({
        source: 'generated',
        scenarios: chosen.map<ScenarioInput>((s) => ({
          scenario_key: s.scenario_key,
          prompt: s.prompt,
          expected_answer: s.expected_answer,
          persona_criteria: s.persona_criteria,
          instruction_criteria: s.instruction_criteria,
          tags: s.tags.length ? s.tags : null,
          folder_id: resolvedFolderId || null,
        })),
      });
      showToast.success(
        `${result.created} scenario${result.created === 1 ? '' : 's'} added`,
        'Generated from the agent’s published system prompt.',
      );
      onClose();
    } catch (error) {
      handleApiError(error);
    }
  };

  const toggleRow = (key: string) => {
    setSelectedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const toggleAll = () => {
    if (!preview) return;
    setSelectedKeys((prev) =>
      prev.size === preview.length ? new Set() : new Set(preview.map((s) => s.scenario_key)),
    );
  };

  const inPreview = preview !== null;
  const anyPending = generate.isPending || persist.isPending || createFolder.isPending;
  // Cancel = full modal close; Regenerate = go back to the form to
  // re-run generation (keeps count + folder inputs so the user can tweak).
  const modalClose = anyPending ? () => undefined : onClose;

  return (
    <CustomModal
      open={open}
      onClose={modalClose}
      title={inPreview ? 'Review generated scenarios' : 'Auto-generate scenarios'}
      description={
        inPreview
          ? 'Uncheck any scenario you don’t want. Only checked rows will be saved.'
          : 'Uses the org’s judge model + this agent’s system prompt to draft scenarios. You’ll review the drafts before saving.'
      }
      width={inPreview ? 'sm:max-w-5xl' : 'sm:max-w-lg'}
      footer={
        inPreview ? (
          <div className="flex items-center justify-between gap-2">
            <CustomButton
              type="text"
              onClick={() => {
                setPreview(null);
                setSelectedKeys(new Set());
              }}
              disabled={anyPending}
            >
              ← Regenerate
            </CustomButton>
            <div className="flex gap-2">
              <CustomButton type="default" onClick={onClose} disabled={anyPending}>
                Cancel
              </CustomButton>
              <CustomButton
                type="primary"
                onClick={savePreview}
                loading={persist.isPending}
                disabled={selectedKeys.size === 0 || anyPending}
              >
                Save {selectedKeys.size} scenario{selectedKeys.size === 1 ? '' : 's'}
              </CustomButton>
            </div>
          </div>
        ) : (
          <div className="flex justify-end gap-2">
            <CustomButton type="default" onClick={onClose} disabled={anyPending}>
              Cancel
            </CustomButton>
            <CustomButton
              type="primary"
              onClick={runGenerate}
              loading={generate.isPending}
              icon={<Sparkles className="size-3.5" />}
            >
              Generate preview
            </CustomButton>
          </div>
        )
      }
    >
      {inPreview && preview ? (
        <GeneratedScenariosPreview
          rows={preview}
          selectedKeys={selectedKeys}
          onToggleRow={toggleRow}
          onToggleAll={toggleAll}
        />
      ) : (
        <div className="flex flex-col gap-3">
          <TextInput
            name="count"
            label="How many scenarios?"
            type="number"
            min={1}
            max={GENERATE_MAX_COUNT}
            value={count}
            onChange={(e) => setCount(e.target.value)}
            helperText={`Between 1 and ${GENERATE_MAX_COUNT}. Nothing is saved until you review the preview.`}
          />
          <FolderPicker
            folders={folderOptions}
            value={folderId}
            onChange={setFolderId}
            newFolderName={newFolderName}
            onNewFolderNameChange={setNewFolderName}
          />
        </div>
      )}
    </CustomModal>
  );
}

// Preview table for the Auto-generate flow. Kept local to this file
// because it's a one-off shape — nothing else renders ``GeneratedScenario``.
function GeneratedScenariosPreview({
  rows,
  selectedKeys,
  onToggleRow,
  onToggleAll,
}: {
  rows: GeneratedScenario[];
  selectedKeys: Set<string>;
  onToggleRow: (key: string) => void;
  onToggleAll: () => void;
}) {
  const allSelected = rows.length > 0 && selectedKeys.size === rows.length;
  const someSelected = selectedKeys.size > 0 && selectedKeys.size < rows.length;
  const selectAllRef = useRef<HTMLInputElement | null>(null);
  useEffect(() => {
    // Native indeterminate state isn't reachable via a prop — set it
    // imperatively so the "some selected" tri-state renders correctly.
    if (selectAllRef.current) selectAllRef.current.indeterminate = someSelected;
  }, [someSelected]);
  return (
    <div className="flex max-h-[60vh] flex-col overflow-hidden rounded-md border border-border/60">
      <div className="overflow-y-auto">
        <table className="w-full table-fixed text-sm">
          <colgroup>
            <col className="w-10" />
            <col className="w-[220px]" />
            <col />
            <col className="w-[200px]" />
          </colgroup>
          <thead className="sticky top-0 z-10 bg-muted text-[11px] uppercase tracking-wide text-muted-foreground shadow-[0_1px_0_0_var(--border)]">
            <tr>
              <th className="px-3 py-2 text-left">
                <input
                  ref={selectAllRef}
                  type="checkbox"
                  aria-label="Select all"
                  checked={allSelected}
                  onChange={onToggleAll}
                  className="cursor-pointer accent-primary"
                />
              </th>
              <th className="px-3 py-2 text-left">Scenario</th>
              <th className="px-3 py-2 text-left">Prompt</th>
              <th className="px-3 py-2 text-left">Tags</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const checked = selectedKeys.has(r.scenario_key);
              return (
                <tr
                  key={r.scenario_key}
                  className={cn(
                    'cursor-pointer border-t border-border/60 hover:bg-muted/30',
                    !checked && 'opacity-70',
                  )}
                  onClick={() => onToggleRow(r.scenario_key)}
                >
                  <td className="px-3 py-2 align-top">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => onToggleRow(r.scenario_key)}
                      onClick={(e) => e.stopPropagation()}
                      aria-label={`Select ${r.scenario_key}`}
                      className="cursor-pointer accent-primary"
                    />
                  </td>
                  <td className="px-3 py-2 align-top font-medium text-foreground break-words">
                    {r.scenario_key}
                  </td>
                  <td className="px-3 py-2 align-top text-muted-foreground">
                    <span className="line-clamp-3 block break-words" title={r.prompt}>
                      {r.prompt}
                    </span>
                  </td>
                  <td className="px-3 py-2 align-top">
                    <div className="flex flex-wrap gap-1">
                      {r.tags.map((t) => (
                        <span
                          key={t}
                          className="max-w-[160px] truncate rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── New folder modal ────────────────────────────────────────────────────

function NewFolderModal({
  open,
  onClose,
  onSubmit,
  pending,
}: {
  open: boolean;
  onClose: () => void;
  onSubmit: (name: string) => Promise<void> | void;
  pending: boolean;
}) {
  const [name, setName] = useState('');

  useEffect(() => {
    if (!open) setName('');
  }, [open]);

  const submit = () => {
    const trimmed = name.trim();
    if (!trimmed) return;
    onSubmit(trimmed);
  };

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title="New folder"
      description="Group scenarios by feature, flow, or persona — folders survive after their last scenario is deleted."
      width="max-w-md"
      footer={
        <div className="flex justify-end gap-2">
          <CustomButton type="default" onClick={onClose} disabled={pending}>
            Cancel
          </CustomButton>
          <CustomButton
            type="primary"
            onClick={submit}
            loading={pending}
            disabled={pending || !name.trim()}
          >
            Create folder
          </CustomButton>
        </div>
      }
    >
      <TextInput
        name="folder_name"
        label="Folder name"
        placeholder="e.g. Refund flow"
        value={name}
        onChange={(e) => setName(e.target.value)}
        isRequired
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            submit();
          }
        }}
      />
    </CustomModal>
  );
}

// ── Results drawer ──────────────────────────────────────────────────────

function AgentLlmEvalResultsDrawer({
  open,
  onClose,
  agentId,
  runId,
}: {
  open: boolean;
  onClose: () => void;
  agentId: string;
  runId: string | null;
}) {
  const detailQuery = useAgentLlmEvalRunDetail(open ? agentId : null, open ? runId : null);
  const summary = detailQuery.data?.summary;
  const totals = summary?.summary as Record<string, number> | undefined;

  // Every scenario in a run scores against the SAME snapshotted agent
  // config, so the system prompt is identical row-to-row. Pull it once from
  // the first scored scenario and render it in a single collapsible panel
  // at the top of the drawer — the per-row "System prompt at run time"
  // section is removed to avoid duplicating the same text N times.
  const scenarios = detailQuery.data?.scenarios ?? [];
  const sharedSystemPrompt = scenarios.find((s) => s.system_prompt)?.system_prompt ?? null;

  return (
    <CustomDrawer
      open={open}
      onClose={onClose}
      title={summary ? `LLM eval run #${summary.run_number}` : 'LLM eval run'}
      description="Every scored scenario in this batch."
      width="w-[900px] sm:max-w-[95vw]"
    >
      <div className="flex flex-col gap-4">
        {detailQuery.isLoading && (
          <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
            Loading run…
          </div>
        )}
        {summary && totals && (
          <section className="rounded-lg border border-border/60 bg-card p-3">
            <div className="grid grid-cols-3 gap-3 text-[12.5px] sm:grid-cols-5">
              <SummaryCell label="Score" value={`${totals.pass ?? 0} / ${totals.total ?? 0}`} />
              <SummaryCell
                label="Pass rate"
                value={`${Math.round(((totals.pass_rate ?? 0) as number) * 100)}%`}
              />
              <SummaryCell label="Partial" value={String(totals.partial ?? 0)} />
              <SummaryCell label="Fail" value={String(totals.fail ?? 0)} />
              <SummaryCell label="Judge" value={summary.judge_model ?? '—'} />
            </div>
          </section>
        )}
        {sharedSystemPrompt && <AgentPromptPanel prompt={sharedSystemPrompt} />}
        {detailQuery.data?.scenarios.map((s) => (
          <ScoredScenarioRow key={s.id} scored={s} />
        ))}
        {detailQuery.data && detailQuery.data.scenarios.length === 0 && (
          <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
            No scored scenarios yet.
          </div>
        )}
      </div>
    </CustomDrawer>
  );
}

function AgentPromptPanel({ prompt }: { prompt: string }) {
  // Expanded by default so users see the full prompt as they enter — it's
  // the most-referenced context in the drawer. Collapsible so long prompts
  // don't push scored scenarios off-screen.
  const [expanded, setExpanded] = useState(true);
  return (
    <section className="rounded-lg border border-border/60 bg-card">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left"
        aria-expanded={expanded}
      >
        {expanded ? (
          <ChevronDown className="size-4 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
        )}
        <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          Agent system prompt at run time
        </span>
        <span className="ml-auto text-[10px] text-muted-foreground/70">
          {expanded ? 'Hide' : 'Show'}
        </span>
      </button>
      {expanded && (
        <div className="max-h-72 overflow-auto whitespace-pre-wrap border-t border-border/60 px-3 py-3 font-mono text-[12px] text-foreground">
          {prompt}
        </div>
      )}
    </section>
  );
}

function SummaryCell({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-0.5 font-medium tabular-nums text-foreground">{value}</div>
    </div>
  );
}

function ScoredScenarioRow({ scored }: { scored: AgentLlmEvalScoredScenario }) {
  const [expanded, setExpanded] = useState(false);
  // Per-scenario "system prompt at run time" section was removed — the
  // prompt is identical across every scored row in a run, so it lives once
  // at the top of the drawer (see ``AgentPromptPanel``).
  return (
    <div className="rounded-md border border-border/60 bg-card">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-start gap-2 px-3 py-2 text-left"
        aria-expanded={expanded}
      >
        {expanded ? (
          <ChevronDown className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
        )}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <VerdictChip verdict={scored.verdict} />
            <span className="text-[11px] text-muted-foreground">{scored.scenario_key}</span>
            {scored.folder && (
              <span
                title={`Folder: ${scored.folder}`}
                className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground ring-1 ring-border"
              >
                <FolderIcon className="size-2.5" />
                {scored.folder}
              </span>
            )}
            {scored.latency_ms != null && (
              <span className="ml-auto text-[11px] tabular-nums text-muted-foreground">
                {scored.latency_ms}ms
              </span>
            )}
          </div>
          <div className="mt-1 line-clamp-2 text-[13px] font-medium text-foreground">
            {scored.prompt}
          </div>
        </div>
      </button>
      {expanded && (
        <div className="grid grid-cols-1 gap-3 border-t border-border/60 px-3 py-3 text-[12.5px] md:grid-cols-2">
          <div>
            <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
              Expected
            </div>
            <div className="mt-1 whitespace-pre-wrap text-foreground">
              {scored.expected_answer ?? '—'}
            </div>
          </div>
          <div>
            <div className="text-[11px] uppercase tracking-wide text-muted-foreground">Actual</div>
            <div className="mt-1 whitespace-pre-wrap text-foreground">
              {scored.actual_answer ?? '—'}
            </div>
          </div>
          {scored.judge_reasoning && (
            <div className="md:col-span-2">
              <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                Judge reasoning
              </div>
              <div className="mt-1 whitespace-pre-wrap text-foreground">
                {formatIngestionError(scored.judge_reasoning) ?? scored.judge_reasoning}
              </div>
            </div>
          )}
          {/* Tool call intents (Phase 2). Only surfaces when the executor
              actually captured tool_calls — no-tool scenarios stay quiet.
              The deterministic ``tool_selection`` metric verdict + reason
              live under Metrics + Judge reasoning above, so this section
              is inspection-only ("what did the LLM ask to call?"). */}
          {scored.tools_called && scored.tools_called.length > 0 && (
            <div className="md:col-span-2">
              <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-muted-foreground">
                <Wrench className="size-3" />
                Tool call intents
              </div>
              <div className="mt-1 flex flex-col gap-2">
                {scored.tools_called.map((intent, i) => (
                  <div
                    // Tool call intents are ordered + repeatable (same tool
                    // may be called twice), so index-in-list is the stable
                    // React key; ``name`` alone would collide.
                    key={`${intent.name}-${i}`}
                    className="rounded border border-border/60 bg-muted/40 px-2 py-1.5"
                  >
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono text-[11.5px] font-medium text-foreground">
                        {intent.name}
                      </span>
                    </div>
                    {intent.arguments && Object.keys(intent.arguments).length > 0 && (
                      <pre className="mt-1 overflow-x-auto whitespace-pre-wrap break-all text-[11px] text-muted-foreground">
                        {JSON.stringify(intent.arguments, null, 2)}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
          {scored.metric_scores && Object.keys(scored.metric_scores).length > 0 && (
            <div className="md:col-span-2">
              <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                Metrics
              </div>
              <div className="mt-1 flex flex-wrap gap-3">
                {Object.entries(scored.metric_scores).map(([name, entry]) => (
                  <div key={name} className="rounded bg-muted px-2 py-1 text-[11px]">
                    <span className="font-medium text-foreground">{name}</span>{' '}
                    <span className="tabular-nums text-muted-foreground">
                      {entry?.score != null ? entry.score.toFixed(2) : '—'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {(scored.answer_error || scored.judge_error) && (
            <div className="md:col-span-2">
              <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                Errors
              </div>
              {scored.answer_error && (
                <div className="mt-1 text-destructive">
                  Answer: {formatIngestionError(scored.answer_error) ?? scored.answer_error}
                </div>
              )}
              {scored.judge_error && (
                <div className="mt-1 text-destructive">
                  Judge: {formatIngestionError(scored.judge_error) ?? scored.judge_error}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
