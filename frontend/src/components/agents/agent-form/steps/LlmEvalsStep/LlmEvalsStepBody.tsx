'use client';

import {
  Download,
  Folder as FolderIcon,
  Gauge,
  History,
  MoreVertical,
  Play,
  Sparkles,
  Trash2,
  Upload,
} from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import SectionCard from '@/components/agents/agent-form/SectionCard';
import ConfirmDeleteModal from '@/components/contacts/shared/ConfirmDeleteModal';
import { CustomButton, CustomTab, SearchBar } from '@/components/shared';
import type { TabItem } from '@/components/shared';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  useAgentLlmEvalFolders,
  useAgentLlmEvalRuns,
  useAgentLlmEvalScenarios,
  useCreateAgentLlmEvalFolder,
  useDeleteAgentLlmEvalFolder,
  useDeleteAgentLlmEvalScenario,
  useDeleteAgentLlmEvalScenariosBulk,
  useRenameAgentLlmEvalFolder,
  useTriggerAgentLlmEvalRun,
  useUploadAgentLlmEvalScenariosCsv,
} from '@/lib/api/agentLlmEvals';
import type { AgentLlmEvalScenario, AgentLlmEvalScenarioSource } from '@/types/agentLlmEval';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

import AgentLlmEvalResultsDrawer from './AgentLlmEvalResultsDrawer';
import FolderBreadcrumb from './FolderBreadcrumb';
import FoldersView from './FoldersView';
import GenerateScenariosModal from './GenerateScenariosModal';
import { downloadSampleCsv } from './helpers';
import LlmEvalsPagination from './LlmEvalsPagination';
import NewFolderModal from './NewFolderModal';
import RunEvalModal from './RunEvalModal';
import RunsTable from './RunsTable';
import ScenarioFormModal from './ScenarioFormModal';
import ScenariosSourceFilter from './ScenariosSourceFilter';
import ScenariosTable from './ScenariosTable';
import type { FolderScope, LlmEvalsView } from './types';

export default function LlmEvalsStepBody({ agentId }: { agentId: string }) {
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

  // Hoisted multi-line handlers (repo rule: no multi-line inline JSX arrows).
  const handleCsvInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] ?? null;
    handleCsvPick(f);
    e.target.value = '';
  };

  const handleNewScenario = () => {
    setEditing(null);
    setOpenCreate(true);
  };

  const handleEditScenario = (s: AgentLlmEvalScenario) => {
    setEditing(s);
    setOpenCreate(true);
  };

  const handleScenariosPageSizeChange = (size: number) => {
    setPageSize(size);
    setPage(1);
  };

  const handleRunsPageSizeChange = (size: number) => {
    setRunsPageSize(size);
    setRunsPage(1);
  };

  const handleCloseNewFolder = () => {
    if (!createFolder.isPending) setOpenNewFolder(false);
  };

  const handleCloseDeleteScenario = () => {
    if (!deleteScenario.isPending) setPendingDelete(null);
  };

  const handleCloseBulkDelete = () => {
    if (!deleteScenariosBulk.isPending) setPendingBulkDelete(false);
  };

  const handleCloseDeleteFolder = () => {
    if (!deleteFolder.isPending) setPendingDeleteFolderId(null);
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
        onChange={handleCsvInputChange}
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
      <CustomButton type="default" size="sm" onClick={handleNewScenario}>
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
            onEdit={handleEditScenario}
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
            onPageSizeChange={handleScenariosPageSizeChange}
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
        onPageSizeChange={handleRunsPageSizeChange}
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
        onClose={handleCloseNewFolder}
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
        onClose={handleCloseDeleteScenario}
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
        onClose={handleCloseBulkDelete}
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
        onClose={handleCloseDeleteFolder}
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
