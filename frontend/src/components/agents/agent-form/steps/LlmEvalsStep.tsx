'use client';

import {
  ArrowLeft,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Folder as FolderIcon,
  Gauge,
  History,
  MinusCircle,
  Pencil,
  Play,
  Sparkles,
  Trash2,
  Upload,
  Wrench,
  XCircle,
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';

import SectionCard from '@/components/agents/agent-form/SectionCard';
import ConfirmDeleteModal from '@/components/contacts/shared/ConfirmDeleteModal';
import {
  CustomButton,
  CustomDrawer,
  CustomModal,
  CustomTab,
  SearchBar,
  SelectInput,
  TextAreaField,
  TextInput,
} from '@/components/shared';
import type { TabItem } from '@/components/shared';
import {
  useAgentLlmEvalFolders,
  useAgentLlmEvalRunDetail,
  useAgentLlmEvalRuns,
  useAgentLlmEvalScenarios,
  useCreateAgentLlmEvalScenario,
  useDeleteAgentLlmEvalScenario,
  useGenerateAgentLlmEvalScenarios,
  useRenameAgentLlmEvalFolder,
  useTriggerAgentLlmEvalRun,
  useUpdateAgentLlmEvalScenario,
  useUploadAgentLlmEvalScenariosCsv,
} from '@/lib/api/agentLlmEvals';
import type {
  AgentLlmEvalFolder,
  AgentLlmEvalRunSummary,
  AgentLlmEvalScenario,
  AgentLlmEvalScoredScenario,
  AgentLlmEvalVerdict,
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

// ── Folder scope ────────────────────────────────────────────────────────

// The selected folder in the sidebar. ``null`` = "All", ``''`` (empty
// string) = "Uncategorized" (matches DB rows with NULL folder), any other
// string = that named folder. Kept as one type so downstream props /
// payloads never accidentally lose the null-vs-empty distinction.
export type FolderScope = null | string;

// Sub-tab identity inside the LLM Evals section. Kept as a named union so
// the tab key + the state setter agree on the exact strings — a typo in
// one place fails at compile time instead of silently rendering nothing.
type LlmEvalsView = 'folders' | 'runs';

const UNCATEGORIZED_LABEL = 'Uncategorized';

// Sentinel option value used by ``FolderPicker``'s inline SelectInput to
// represent NULL/Uncategorized. Any string not otherwise a folder name is
// fine; using a reserved token avoids clashing with a real folder called
// "" or "Uncategorized".
const UNCAT_OPTION_VALUE = '__uncategorized__';
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

  // Folder scope selector. ``null`` = All (no filter). ``''`` = Uncategorized
  // (matches rows with NULL folder). Any other string = that named folder.
  const [selectedFolder, setSelectedFolder] = useState<FolderScope>(null);
  const [renameFolder, setRenameFolder] = useState<string | null>(null);
  // Sub-tab inside the LLM Evals section — 'folders' (default: scenario
  // management) vs 'runs' (past run history). Kept as local state; not
  // URL-synced in v1. Promote to a query param later if deep-links needed.
  const [activeView, setActiveView] = useState<LlmEvalsView>('folders');

  const scenariosQuery = useAgentLlmEvalScenarios(agentId, {
    search: search || undefined,
    folder: selectedFolder === null ? undefined : selectedFolder,
    page_size: 200,
  });
  const foldersQuery = useAgentLlmEvalFolders(agentId);
  const runsQuery = useAgentLlmEvalRuns(agentId);
  const uploadCsv = useUploadAgentLlmEvalScenariosCsv(agentId);
  const deleteScenario = useDeleteAgentLlmEvalScenario(agentId);
  const triggerRun = useTriggerAgentLlmEvalRun(agentId);

  const scenarios = scenariosQuery.data?.items ?? [];
  const runs = runsQuery.data ?? [];
  const scenarioCount = scenariosQuery.data?.total ?? scenarios.length;
  const folders = foldersQuery.data?.items ?? [];
  const totalScenariosAllFolders = folders.reduce((n, f) => n + f.count, 0);

  // Quick-run one folder from a card / breadcrumb.
  //   - ``null``      → Uncategorized card → send folder='' (matches NULL rows)
  //   - ``''``        → drilled into Uncategorized → same as above
  //   - ``'<name>'``  → that named folder
  // Uses the singular ``folder`` field intentionally (single-folder path).
  // Multi-folder runs go through the RunEvalModal with the plural ``folders``
  // field instead. The two never mix in one request.
  const runFolder = async (folderName: string | null) => {
    const folderValue = folderName === null ? '' : folderName;
    try {
      const result = await triggerRun.mutateAsync({ folder: folderValue });
      showToast.success(
        'Eval queued',
        `Job #${result.job_id} — results appear once the worker completes.`,
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

  const inFolderView = selectedFolder !== null;
  const activeFolderCount = inFolderView
    ? (folders.find((f) => (f.folder ?? '') === selectedFolder)?.count ?? 0)
    : 0;

  const foldersPanel = (
    <SectionCard
      icon={<Gauge className="size-4" />}
      iconClassName="bg-violet-500/10 text-violet-700 dark:text-violet-400 ring-violet-500/20"
      title="LLM Evals"
      description="Score this agent's LLM output against your scenarios."
      action={
        <span className="text-[11px] uppercase tracking-wide text-muted-foreground">
          {inFolderView
            ? `${scenarioCount} scenario${scenarioCount === 1 ? '' : 's'}`
            : `${folders.length} folder${folders.length === 1 ? '' : 's'} · ${totalScenariosAllFolders} scenario${totalScenariosAllFolders === 1 ? '' : 's'}`}
        </span>
      }
    >
      {/* Toolbar: search (only when drilled into a folder) on the left,
          action buttons always on the right. The right-aligned action group
          is a single ``ml-auto`` container so its position is stable whether
          or not the SearchBar is rendered — no per-view special-casing. */}
      <div className="flex flex-wrap items-center gap-2">
        {inFolderView && (
          <div className="min-w-[200px] flex-1">
            <SearchBar
              value={search}
              onChange={(v) => setSearch(v)}
              placeholder="Search scenarios…"
            />
          </div>
        )}
        <div className="ml-auto flex flex-wrap items-center justify-end gap-2">
          <CustomButton
            type="default"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadCsv.isPending}
            icon={<Upload className="size-4" />}
          >
            {uploadCsv.isPending ? 'Uploading…' : 'Import CSV'}
          </CustomButton>
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
            onClick={() => setOpenGenerate(true)}
            icon={<Sparkles className="size-4" />}
          >
            Auto-generate
          </CustomButton>
          <CustomButton
            type="default"
            onClick={() => {
              setEditing(null);
              setOpenCreate(true);
            }}
          >
            New Scenario
          </CustomButton>
          <CustomButton
            type="primary"
            onClick={() => setOpenRun(true)}
            disabled={totalScenariosAllFolders === 0}
            icon={<Play className="size-4" />}
          >
            Run Eval
          </CustomButton>
        </div>
      </div>

      {inFolderView ? (
        <>
          <FolderBreadcrumb
            folderName={selectedFolder as string}
            count={activeFolderCount}
            onBack={() => setSelectedFolder(null)}
            onRunFolder={() => runFolder(selectedFolder as string)}
            onRename={
              // Uncategorized ('' = NULL folder) cannot be renamed — there's
              // no actual name to change and NULL isn't a rename target.
              selectedFolder ? () => setRenameFolder(selectedFolder) : undefined
            }
            isRunning={triggerRun.isPending}
          />
          <ScenariosTable
            scenarios={scenarios}
            isLoading={scenariosQuery.isLoading}
            onEdit={(s) => {
              setEditing(s);
              setOpenCreate(true);
            }}
            onDelete={handleDelete}
          />
        </>
      ) : (
        <FoldersView
          folders={folders}
          isLoading={foldersQuery.isLoading}
          onOpen={setSelectedFolder}
          onRunFolder={runFolder}
          onRename={(name) => setRenameFolder(name)}
          isRunning={triggerRun.isPending}
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
          {runs.length} run{runs.length === 1 ? '' : 's'}
        </span>
      }
    >
      <RunsTable
        runs={runs}
        isLoading={runsQuery.isLoading}
        onOpen={setOpenRunId}
        onEmptyCTA={() => setActiveView('folders')}
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
          {runs.length > 0 && (
            <span className="inline-flex min-w-[1.25rem] items-center justify-center rounded-full bg-muted px-1.5 py-0.5 text-[10.5px] font-semibold text-muted-foreground">
              {runs.length}
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
        defaultFolder={typeof selectedFolder === 'string' ? selectedFolder : ''}
      />
      <RunEvalModal
        open={openRun}
        onClose={() => setOpenRun(false)}
        agentId={agentId}
        scenarios={scenarios}
        folders={folders}
        defaultFolder={selectedFolder}
      />
      <GenerateScenariosModal
        open={openGenerate}
        onClose={() => setOpenGenerate(false)}
        agentId={agentId}
        folderOptions={folders}
        defaultFolder={typeof selectedFolder === 'string' ? selectedFolder : ''}
      />
      <RenameFolderModal
        open={renameFolder !== null}
        onClose={() => setRenameFolder(null)}
        agentId={agentId}
        oldName={renameFolder}
        folders={folders}
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
    </div>
  );
}

// ── Scenarios table ─────────────────────────────────────────────────────

function ScenariosTable({
  scenarios,
  isLoading,
  onEdit,
  onDelete,
}: {
  scenarios: AgentLlmEvalScenario[];
  isLoading: boolean;
  onEdit: (s: AgentLlmEvalScenario) => void;
  onDelete: (s: AgentLlmEvalScenario) => void;
}) {
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
            <th className="px-3 py-2 text-left">Scenario</th>
            <th className="px-3 py-2 text-left">Prompt</th>
            {/* Fixed-width tags + source columns so the Prompt column can
                grow into the leftover space without squeezing them to a
                sliver (which caused tag chips to wrap vertically). */}
            <th className="w-[220px] px-3 py-2 text-left">Tags</th>
            <th className="w-[100px] px-3 py-2 text-left">Source</th>
            <th className="w-[80px] px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          {scenarios.map((s) => (
            <tr key={s.id} className="border-t border-border/60">
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
                    onClick={() => onEdit(s)}
                    className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                    aria-label="Edit scenario"
                  >
                    <Pencil className="size-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => onDelete(s)}
                    className="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
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

// ── Runs table ──────────────────────────────────────────────────────────

function RunsTable({
  runs,
  isLoading,
  onOpen,
  onEmptyCTA,
}: {
  runs: AgentLlmEvalRunSummary[];
  isLoading: boolean;
  onOpen: (runId: string) => void;
  onEmptyCTA?: () => void;
}) {
  if (isLoading) {
    return (
      <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
        Loading runs…
      </div>
    );
  }
  if (runs.length === 0) {
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
            return (
              <tr
                key={r.run_id}
                className="cursor-pointer border-t border-border/60 hover:bg-muted/30"
                onClick={() => onOpen(r.run_id)}
              >
                <td className="px-3 py-2 font-medium text-foreground">#{r.run_number}</td>
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
                </td>
                <td className="px-3 py-2 text-right text-muted-foreground">
                  <ChevronRight className="ml-auto size-4" />
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
 * that folder's scenarios (see ``FolderBreadcrumb``). Uncategorized (rows
 * with NULL folder) appears as a card too when any exist. Empty state and
 * loading state are handled here so the caller stays declarative. */
function FoldersView({
  folders,
  isLoading,
  onOpen,
  onRunFolder,
  onRename,
  isRunning,
}: {
  folders: AgentLlmEvalFolder[];
  isLoading: boolean;
  onOpen: (folder: FolderScope) => void;
  onRunFolder: (folder: string | null) => void;
  onRename: (folder: string) => void;
  isRunning: boolean;
}) {
  if (isLoading) {
    return (
      <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
        Loading folders…
      </div>
    );
  }
  const uncategorized = folders.find((f) => f.folder === null);
  const named = folders.filter((f) => f.folder !== null);
  const hasAny = named.length > 0 || (uncategorized?.count ?? 0) > 0;
  if (!hasAny) {
    return (
      <div className="rounded-md border border-dashed border-border/60 p-6 text-center text-sm text-muted-foreground">
        No scenarios yet. Create one, import a CSV, or use Auto-generate.
      </div>
    );
  }
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {named.map((f) => (
        <FolderCard
          key={f.folder as string}
          name={f.folder as string}
          count={f.count}
          canRename
          onOpen={() => onOpen(f.folder)}
          onRun={() => onRunFolder(f.folder)}
          onRename={() => onRename(f.folder as string)}
          isRunning={isRunning}
        />
      ))}
      {uncategorized && uncategorized.count > 0 && (
        <FolderCard
          name={UNCATEGORIZED_LABEL}
          count={uncategorized.count}
          canRename={false}
          isMuted
          onOpen={() => onOpen('')}
          onRun={() => onRunFolder(null)}
          isRunning={isRunning}
        />
      )}
    </div>
  );
}

/** One folder tile — clickable to open, with quick Run + Rename actions
 * always visible at the bottom (muted → foreground on hover). The whole
 * card is a ``<button>``; nested actions use ``<span role="button">`` +
 * ``e.stopPropagation()`` (invalid to nest ``<button>`` inside a button).
 * Uncategorized passes ``isMuted`` for a slightly softer background and
 * ``canRename=false`` (NULL folder has no name to rename). */
function FolderCard({
  name,
  count,
  canRename,
  isMuted = false,
  onOpen,
  onRun,
  onRename,
  isRunning,
}: {
  name: string;
  count: number;
  canRename: boolean;
  isMuted?: boolean;
  onOpen: () => void;
  onRun: () => void;
  onRename?: () => void;
  isRunning: boolean;
}) {
  const runDisabled = isRunning || count === 0;
  return (
    <button
      type="button"
      onClick={onOpen}
      className={cn(
        'group relative flex h-full flex-col gap-4 rounded-xl border border-border/60 p-4 text-left',
        'transition-all duration-150 hover:-translate-y-0.5 hover:border-border hover:shadow-sm',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1',
        isMuted ? 'bg-muted/30' : 'bg-card',
      )}
      aria-label={`Open folder ${name}`}
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
          <div
            className="truncate text-[14px] font-semibold leading-tight text-foreground"
            title={name}
          >
            {name}
          </div>
          <div className="mt-1 inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-[10.5px] font-medium text-muted-foreground">
            {count} scenario{count === 1 ? '' : 's'}
          </div>
        </div>
        <ChevronRight
          className={cn(
            'mt-1 size-4 shrink-0 text-muted-foreground/40 transition-all',
            'group-hover:translate-x-0.5 group-hover:text-muted-foreground',
          )}
        />
      </div>

      {/* Bottom action row — always visible, muted by default so the card
          reads clean, brightens on card hover so users know they're
          interactive. Divider gives visual separation without extra chrome. */}
      <div className="mt-auto flex items-center gap-1 border-t border-border/50 pt-3">
        {canRename && onRename && (
          <FolderCardAction
            icon={<Pencil className="size-3.5" />}
            label="Rename"
            onActivate={onRename}
            title={`Rename ${name}`}
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
    </button>
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
  emphasis?: 'default' | 'primary';
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

/** Header shown when the user has drilled into a folder. Two-tier layout:
 *   - Top: subtle "← All folders" text link (secondary; not a heavy button).
 *   - Main: prominent folder icon + name + count on the left, Rename +
 *     Run-this-folder actions on the right.
 * Uncategorized omits Rename (NULL folder has no name to rename). */
function FolderBreadcrumb({
  folderName,
  count,
  onBack,
  onRunFolder,
  onRename,
  isRunning,
}: {
  folderName: string; // '' means Uncategorized
  count: number;
  onBack: () => void;
  onRunFolder: () => void;
  onRename?: () => void;
  isRunning: boolean;
}) {
  const displayName = folderName === '' ? UNCATEGORIZED_LABEL : folderName;
  const isUncategorized = folderName === '';
  return (
    <div className="flex flex-col gap-3">
      {/* Back link — text-only so the visual weight lands on the folder
          title below, not on the navigation affordance. */}
      <button
        type="button"
        onClick={onBack}
        className="inline-flex w-fit cursor-pointer items-center gap-1 text-[12px] font-medium text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="size-3.5" />
        All folders
      </button>

      {/* Title bar — icon + name + count on the left, actions on the right. */}
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-border/60 bg-card px-4 py-3">
        <div
          className={cn(
            'flex size-9 shrink-0 items-center justify-center rounded-lg ring-1',
            isUncategorized
              ? 'bg-muted text-muted-foreground ring-border'
              : 'bg-violet-500/10 text-violet-700 ring-violet-500/20 dark:text-violet-400',
          )}
        >
          <FolderIcon className="size-5" />
        </div>
        <div className="flex min-w-0 flex-col">
          <div
            className="truncate text-[15px] font-semibold leading-tight text-foreground"
            title={displayName}
          >
            {displayName}
          </div>
          <div className="mt-0.5 text-[11.5px] text-muted-foreground">
            {count} scenario{count === 1 ? '' : 's'}
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2">
          {onRename && (
            <CustomButton type="default" onClick={onRename} icon={<Pencil className="size-4" />}>
              Rename
            </CustomButton>
          )}
          <CustomButton
            type="primary"
            onClick={onRunFolder}
            disabled={isRunning || count === 0}
            icon={<Play className="size-4" />}
          >
            Run this folder
          </CustomButton>
        </div>
      </div>
    </div>
  );
}

/** Shared folder picker for the create/edit and generate modals.
 *
 * Two states in one component: a dropdown of existing folders (plus
 * "Uncategorized" and "Create new folder…") OR a text input when the user
 * chose to create a new one. Values are always plain strings — ``''``
 * means Uncategorized/NULL folder. Extracted so all three modals share
 * one shape and one autocomplete list (single source of truth for folder
 * names on the client). */
function FolderPicker({
  folders,
  value,
  onChange,
  label = 'Folder',
}: {
  folders: AgentLlmEvalFolder[];
  value: string;
  onChange: (v: string) => void;
  label?: string;
}) {
  const [mode, setMode] = useState<'select' | 'new'>('select');

  const namedOptions = useMemo(
    () =>
      folders
        .filter((f) => f.folder !== null)
        .map((f) => ({ value: f.folder as string, label: f.folder as string })),
    [folders],
  );

  const options = useMemo(
    () => [
      { value: UNCAT_OPTION_VALUE, label: UNCATEGORIZED_LABEL },
      ...namedOptions,
      { value: NEW_FOLDER_OPTION_VALUE, label: '+ Create new folder…' },
    ],
    [namedOptions],
  );

  const selectValue = value === '' ? UNCAT_OPTION_VALUE : value;

  const handleSelectChange = (v: string | null) => {
    const next = v ?? UNCAT_OPTION_VALUE;
    if (next === NEW_FOLDER_OPTION_VALUE) {
      setMode('new');
      onChange('');
      return;
    }
    if (next === UNCAT_OPTION_VALUE) {
      onChange('');
      return;
    }
    onChange(next);
  };

  if (mode === 'new') {
    return (
      <div className="flex flex-col gap-1">
        <TextInput
          name="folder_new"
          label={label}
          placeholder="New folder name (leave blank for Uncategorized)"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
        <button
          type="button"
          className="self-start text-[11px] text-muted-foreground underline underline-offset-2 hover:text-foreground"
          onClick={() => {
            setMode('select');
            onChange('');
          }}
        >
          Pick an existing folder instead
        </button>
      </div>
    );
  }

  return (
    <SelectInput
      name="folder"
      label={label}
      value={selectValue}
      onValueChange={handleSelectChange}
      options={options}
    />
  );
}

// ── Rename folder modal ─────────────────────────────────────────────────

function RenameFolderModal({
  open,
  onClose,
  agentId,
  oldName,
  folders,
}: {
  open: boolean;
  onClose: () => void;
  agentId: string;
  oldName: string | null;
  folders: AgentLlmEvalFolder[];
}) {
  const rename = useRenameAgentLlmEvalFolder(agentId);
  const [newName, setNewName] = useState('');

  useEffect(() => {
    if (open) setNewName(oldName ?? '');
    else setNewName('');
  }, [open, oldName]);

  const affectedCount = useMemo(() => {
    if (!oldName) return 0;
    return folders.find((f) => f.folder === oldName)?.count ?? 0;
  }, [folders, oldName]);

  const submit = async () => {
    if (!oldName) return;
    const trimmed = newName.trim();
    if (!trimmed || trimmed === oldName) return;
    try {
      const result = await rename.mutateAsync({
        old_name: oldName,
        new_name: trimmed,
      });
      showToast.success(
        'Folder renamed',
        `${result.scenarios_updated} scenario${result.scenarios_updated === 1 ? '' : 's'} and ${result.results_updated} past result${result.results_updated === 1 ? '' : 's'} moved.`,
      );
      onClose();
    } catch (error) {
      handleApiError(error);
    }
  };

  const trimmed = newName.trim();
  const canSubmit = !!oldName && !!trimmed && trimmed !== oldName && !rename.isPending;

  return (
    <CustomModal
      open={open}
      onClose={rename.isPending ? () => undefined : onClose}
      title="Rename folder"
      description="Renames the folder on every scenario AND on every past run result so history stays grouped under the new name."
      width="max-w-md"
      footer={
        <div className="flex justify-end gap-2">
          <CustomButton type="default" onClick={onClose} disabled={rename.isPending}>
            Cancel
          </CustomButton>
          <CustomButton
            type="primary"
            onClick={submit}
            disabled={!canSubmit}
            loading={rename.isPending}
          >
            Rename
          </CustomButton>
        </div>
      }
    >
      <div className="flex flex-col gap-3">
        <TextInput name="old_folder" label="Current name" value={oldName ?? ''} disabled />
        <TextInput
          name="new_folder"
          label="New name"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="e.g. Refunds"
          isRequired
        />
        {affectedCount > 0 && (
          <p className="text-[12px] text-muted-foreground">
            This will rename {affectedCount} scenario{affectedCount === 1 ? '' : 's'} plus any past
            run results tagged with this folder.
          </p>
        )}
      </div>
    </CustomModal>
  );
}

// ── Scenario create/edit modal ──────────────────────────────────────────

function ScenarioFormModal({
  open,
  onClose,
  agentId,
  scenario,
  folderOptions,
  defaultFolder,
}: {
  open: boolean;
  onClose: () => void;
  agentId: string;
  scenario: AgentLlmEvalScenario | null;
  folderOptions: AgentLlmEvalFolder[];
  defaultFolder: string;
}) {
  const isEdit = !!scenario;
  const create = useCreateAgentLlmEvalScenario(agentId);
  const update = useUpdateAgentLlmEvalScenario(agentId);

  const [key, setKey] = useState('');
  const [prompt, setPrompt] = useState('');
  const [expected, setExpected] = useState('');
  const [persona, setPersona] = useState('');
  const [instruction, setInstruction] = useState('');
  const [tags, setTags] = useState('');
  // '' = Uncategorized (NULL folder); non-empty string = named folder.
  const [folder, setFolder] = useState('');

  useEffect(() => {
    if (!open) return;
    setKey(scenario?.scenario_key ?? '');
    setPrompt(scenario?.prompt ?? '');
    setExpected(scenario?.expected_answer ?? '');
    setPersona(scenario?.persona_criteria ?? '');
    setInstruction(scenario?.instruction_criteria ?? '');
    setTags((scenario?.tags ?? []).join(', '));
    // Edit: pre-fill from the row. Create: pre-fill from the sidebar's
    // current folder selection (falls back to '' = Uncategorized).
    setFolder(scenario?.folder ?? defaultFolder ?? '');
  }, [open, scenario, defaultFolder]);

  const submit = async () => {
    const parsedTags = tags
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);
    const trimmedFolder = folder.trim();
    try {
      if (isEdit && scenario) {
        // Only send fields the user actually changed — otherwise a
        // concurrent edit (another tab / user) gets silently reverted.
        // Tags need a stringified-set compare because the DB stores them
        // as a JSONB array whose order we shouldn't rely on for equality.
        const originalTags = (scenario.tags ?? []).slice().sort().join(',');
        const nextTags = parsedTags.slice().sort().join(',');
        const originalFolder = scenario.folder ?? '';
        const patch: ScenarioPatch = {
          scenario_key: key !== scenario.scenario_key ? key : undefined,
          prompt: prompt !== scenario.prompt ? prompt : undefined,
          expected_answer: expected !== (scenario.expected_answer ?? '') ? expected : undefined,
          persona_criteria: persona !== (scenario.persona_criteria ?? '') ? persona : undefined,
          instruction_criteria:
            instruction !== (scenario.instruction_criteria ?? '') ? instruction : undefined,
          tags: nextTags !== originalTags ? parsedTags : undefined,
          folder: trimmedFolder !== originalFolder ? trimmedFolder : undefined,
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
          folder: trimmedFolder || null,
        };
        await create.mutateAsync(input);
        showToast.success('Scenario created');
      }
      onClose();
    } catch (error) {
      handleApiError(error);
    }
  };

  const pending = create.isPending || update.isPending;

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
        <FolderPicker folders={folderOptions} value={folder} onChange={setFolder} />
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
  defaultFolder,
}: {
  open: boolean;
  onClose: () => void;
  agentId: string;
  scenarios: AgentLlmEvalScenario[];
  folders: AgentLlmEvalFolder[];
  defaultFolder: FolderScope;
}) {
  const trigger = useTriggerAgentLlmEvalRun(agentId);
  const [judge, setJudge] = useState('');
  const [scope, setScope] = useState<'all' | 'tags' | 'folders'>('all');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  // Each entry: '' = Uncategorized (matches NULL folder), any other string
  // = that named folder. Chip-toggle multi-select mirroring the tag picker.
  const [selectedFolders, setSelectedFolders] = useState<string[]>([]);

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
        value: f.folder ?? '',
        label: f.folder ?? UNCATEGORIZED_LABEL,
        count: f.count,
      })),
    [folders],
  );

  useEffect(() => {
    if (!open) {
      setJudge('');
      setScope('all');
      setSelectedTags([]);
      setSelectedFolders([]);
      return;
    }
    // If a folder was open when the user opened the modal, pre-seed the
    // multi-select with that one folder — saves them re-picking. They can
    // then check additional folders before running.
    if (defaultFolder !== null) {
      setScope('folders');
      setSelectedFolders([defaultFolder]);
    }
  }, [open, defaultFolder]);

  const selectedFoldersCount = useMemo(() => {
    if (!selectedFolders.length) return 0;
    return folderOptions
      .filter((o) => selectedFolders.includes(o.value))
      .reduce((n, o) => n + o.count, 0);
  }, [selectedFolders, folderOptions]);

  const toggleFolder = (value: string) => {
    setSelectedFolders((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value],
    );
  };

  const canSubmit = scope !== 'folders' || (selectedFolders.length > 0 && selectedFoldersCount > 0);

  const submit = async () => {
    try {
      const result = await trigger.mutateAsync({
        judge_model: judge.trim() || undefined,
        tags: scope === 'tags' && selectedTags.length ? selectedTags : undefined,
        // Send the plural `folders` field on multi-select. Backend prefers
        // `folders` when both are provided, so `folder` (singular) is
        // deliberately omitted here.
        folders: scope === 'folders' && selectedFolders.length ? selectedFolders : undefined,
      });
      showToast.success(
        'Eval queued',
        `Job #${result.job_id} — results appear once the worker completes.`,
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
                const active = selectedFolders.includes(f.value);
                const isEmpty = f.count === 0;
                return (
                  <button
                    type="button"
                    key={f.value || '__uncat__'}
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
              {selectedFolders.length === 0
                ? 'Pick one or more folders.'
                : `${selectedFoldersCount} scenario${selectedFoldersCount === 1 ? '' : 's'} across ${selectedFolders.length} folder${selectedFolders.length === 1 ? '' : 's'} will run.`}
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
  defaultFolder,
}: {
  open: boolean;
  onClose: () => void;
  agentId: string;
  folderOptions: AgentLlmEvalFolder[];
  defaultFolder: string;
}) {
  const generate = useGenerateAgentLlmEvalScenarios(agentId);
  const [count, setCount] = useState(String(GENERATE_DEFAULT_COUNT));
  const [folder, setFolder] = useState('');

  useEffect(() => {
    if (!open) {
      setCount(String(GENERATE_DEFAULT_COUNT));
      setFolder('');
      return;
    }
    setFolder(defaultFolder ?? '');
  }, [open, defaultFolder]);

  const submit = async () => {
    const parsedCount = Math.max(
      1,
      Math.min(GENERATE_MAX_COUNT, Number(count) || GENERATE_DEFAULT_COUNT),
    );
    const trimmedFolder = folder.trim();
    try {
      const result = await generate.mutateAsync({
        // Only one strategy is surfaced in v1. ``noop`` stays on the backend
        // as a safety net + test target.
        strategy: 'llm',
        count: parsedCount,
        // Persist directly — the ``persisted`` list on the response drives
        // the scenarios-table refresh via ``useGenerateAgentLlmEvalScenarios``'s
        // shared invalidator.
        dry_run: false,
        folder: trimmedFolder || null,
      });
      const added = result.persisted.length;
      if (added === 0) {
        showToast.info(
          'Auto-generate',
          result.note ??
            'The generator returned no usable scenarios. Try again, or tweak the agent’s system prompt.',
        );
      } else {
        showToast.success(
          `${added} scenario${added === 1 ? '' : 's'} added`,
          'Generated from the agent’s published system prompt.',
        );
      }
      onClose();
    } catch (error) {
      handleApiError(error);
    }
  };

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title="Auto-generate scenarios"
      description="Uses the org’s judge model + this agent’s system prompt to draft scenarios and save them."
      width="max-w-lg"
      footer={
        <div className="flex justify-end gap-2">
          <CustomButton type="default" onClick={onClose} disabled={generate.isPending}>
            Cancel
          </CustomButton>
          <CustomButton type="primary" onClick={submit} loading={generate.isPending}>
            Generate
          </CustomButton>
        </div>
      }
    >
      <div className="flex flex-col gap-3">
        <TextInput
          name="count"
          label="How many scenarios?"
          type="number"
          min={1}
          max={GENERATE_MAX_COUNT}
          value={count}
          onChange={(e) => setCount(e.target.value)}
          helperText={`Between 1 and ${GENERATE_MAX_COUNT}. Existing scenarios are never overwritten — duplicates skip.`}
        />
        <FolderPicker folders={folderOptions} value={folder} onChange={setFolder} />
      </div>
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
                {scored.judge_reasoning}
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
                <div className="mt-1 text-destructive">Answer: {scored.answer_error}</div>
              )}
              {scored.judge_error && (
                <div className="mt-1 text-destructive">Judge: {scored.judge_error}</div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
