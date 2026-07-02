'use client';

import { motion } from 'framer-motion';
import { useSetAtom } from 'jotai';
import { Lock, Plus, RefreshCw, SearchX, TriangleAlert } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useFormContext, useWatch } from 'react-hook-form';

import { deleteWorkflowAtom, fetchWorkflowListAtom } from '@/atoms/WorkflowAtom';
import { useAgentFormNav } from '@/components/agents/agent-form/AgentFormNav';
import AgentWorkflowCard from '@/components/agents/agent-workflows/AgentWorkflowCard';
import CloneWorkflowModal from '@/components/workflows/CloneWorkflowModal';
import CreateWorkflowModal from '@/components/workflows/CreateWorkflowModal';
import WorkflowCardSkeleton from '@/components/workflows/WorkflowCardSkeleton';
import WorkflowEmptyState from '@/components/workflows/WorkflowEmptyState';
import CustomButton from '@/components/shared/CustomButton';
import SearchBar from '@/components/shared/SearchBar';
import type { AgentFormState } from '@/types/agent';
import type { WorkflowSummary } from '@/types/workflow';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

const gridVariants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.04 } },
};
const cardVariants = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: 0.2, ease: 'easeOut' as const } },
};

interface AgentWorkflowsSectionProps {
  /** Owning agent; null while the agent is still being created. */
  agentId: string | null;
  /** Editor base path — used to build the builder return link. */
  basePath: string;
  /** Version number of the agent version currently loaded in the editor. */
  viewedVersion: number | null;
}

/**
 * Workflow-mode body of the Prompt section. Lists the workflows owned by this
 * agent version, lets the user search/create/open/duplicate/delete them, and
 * assign one to the current version. The Prompt/Workflow toggle lives in the
 * parent (PromptStep), so this only renders while workflow mode is active —
 * assignment writes `config.workflow_id` into the agent form and persists
 * through the standard Save flow.
 */
export default function AgentWorkflowsSection({
  agentId,
  basePath,
  viewedVersion,
}: AgentWorkflowsSectionProps) {
  const { safeNavigate } = useAgentFormNav();
  const { setValue } = useFormContext<AgentFormState>();

  const fetchList = useSetAtom(fetchWorkflowListAtom);
  const deleteWorkflow = useSetAtom(deleteWorkflowAtom);

  const [list, setList] = useState<WorkflowSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [errored, setErrored] = useState(false);
  const [loadedOnce, setLoadedOnce] = useState(false);
  const [query, setQuery] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [cloneTarget, setCloneTarget] = useState<WorkflowSummary | null>(null);

  const watchedWorkflowId = useWatch<AgentFormState, 'config.workflow_id'>({
    name: 'config.workflow_id',
  });

  const versionLabel = viewedVersion != null ? `v${viewedVersion}` : 'this version';

  const load = useCallback(async () => {
    if (!agentId) {
      setLoading(false);
      setLoadedOnce(true);
      return;
    }
    setLoading(true);
    setErrored(false);
    try {
      setList(await fetchList({ agentId }));
    } catch {
      setErrored(true);
    } finally {
      setLoading(false);
      setLoadedOnce(true);
    }
  }, [agentId, fetchList]);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return list;
    return list.filter((w) => {
      const versionLabels = (w.assigned_versions ?? []).map((v) => `v${v}`).join(' ');
      const hay = `${w.name} ${w.description ?? ''} ${versionLabels}`.toLowerCase();
      return hay.includes(q);
    });
  }, [list, query]);

  const openBuilder = useCallback(
    (wf: WorkflowSummary) => {
      // Nested under the agent editor — clean URL and no discard prompt (the
      // agent form stays mounted, so this is internal navigation).
      safeNavigate(`${basePath}/workflow/${wf.id}`);
    },
    [basePath, safeNavigate],
  );

  const assign = useCallback(
    (wf: WorkflowSummary) => {
      setValue('config.workflow_id', wf.id, { shouldDirty: true });
      setValue('config.mode', 'workflow', { shouldDirty: true });
    },
    [setValue],
  );

  const unassign = useCallback(() => {
    setValue('config.workflow_id', null, { shouldDirty: true });
  }, [setValue]);

  const handleDelete = useCallback(
    async (wf: WorkflowSummary) => {
      try {
        await deleteWorkflow(wf.id);
        if (watchedWorkflowId === wf.id) {
          unassign();
          showToast.success('Workflow deleted', `Unassigned from ${versionLabel} — click Save.`);
        } else {
          showToast.success('Workflow deleted');
        }
        await load();
      } catch (err) {
        handleApiError(err);
      }
    },
    [deleteWorkflow, load, unassign, versionLabel, watchedWorkflowId],
  );

  // ── create-mode gate — workflows are agent-scoped, so they need a saved agent ──
  if (!agentId) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-border bg-muted/20 px-6 py-14 text-center">
        <span className="flex size-11 items-center justify-center rounded-xl bg-muted text-muted-foreground ring-1 ring-inset ring-border">
          <Lock className="size-5" />
        </span>
        <p className="text-sm font-semibold text-foreground">Save the agent first</p>
        <p className="max-w-sm text-[12.5px] text-muted-foreground">
          Workflows belong to an agent version. Create the agent, then come back here to build and
          assign a workflow.
        </p>
      </div>
    );
  }

  const showSkeleton = loading && !loadedOnce;
  const showError = errored && list.length === 0;
  const showEmpty = loadedOnce && !errored && list.length === 0;
  const noMatches = loadedOnce && !errored && list.length > 0 && filtered.length === 0;

  return (
    <div className="flex flex-col gap-4">
      {/* Header: title + count + New workflow */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h2 className="text-[14px] font-semibold tracking-tight text-foreground">Workflows</h2>
            {loadedOnce && !errored && (
              <span className="rounded-full bg-muted px-2 py-0.5 font-mono text-[11px] text-muted-foreground">
                {list.length}
              </span>
            )}
          </div>
          <p className="mt-0.5 text-[12px] text-muted-foreground">
            Owned by this agent · one independent copy per version.
          </p>
        </div>
        {!showEmpty && (
          <CustomButton
            type="primary"
            size="sm"
            icon={<Plus className="size-4" />}
            onClick={() => setCreateOpen(true)}
          >
            New workflow
          </CustomButton>
        )}
      </div>

      {/* Search — visible during loading too (matches the MCP tools page), hidden
          only on the error screen and the zero-workflows empty state. */}
      {!showError && !showEmpty && (
        <SearchBar
          value={query}
          onChange={setQuery}
          debounceMs={0}
          placeholder="Filter by name or version… (e.g. v4)"
        />
      )}

      {showSkeleton ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <WorkflowCardSkeleton />
          <WorkflowCardSkeleton />
        </div>
      ) : showError ? (
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-destructive/40 bg-destructive/5 px-6 py-12 text-center">
          <TriangleAlert className="h-6 w-6 text-destructive" />
          <p className="text-sm font-medium text-foreground">Couldn’t load workflows</p>
          <p className="max-w-sm text-[12.5px] text-muted-foreground">
            Something went wrong fetching this agent’s workflows. Check your connection and retry.
          </p>
          <CustomButton
            type="default"
            size="sm"
            icon={<RefreshCw className="size-3.5" />}
            onClick={() => void load()}
          >
            Retry
          </CustomButton>
        </div>
      ) : showEmpty ? (
        <WorkflowEmptyState onCreate={() => setCreateOpen(true)} />
      ) : noMatches ? (
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-border bg-muted/20 px-6 py-12 text-center">
          <SearchX className="h-6 w-6 text-muted-foreground" />
          <p className="text-sm font-medium text-foreground">No workflows match your search</p>
          <CustomButton type="text" size="sm" onClick={() => setQuery('')}>
            Clear search
          </CustomButton>
        </div>
      ) : (
        <motion.div
          variants={gridVariants}
          initial="hidden"
          animate="show"
          className="grid grid-cols-1 gap-4 sm:grid-cols-2"
        >
          {filtered.map((wf) => (
            <motion.div key={wf.id} variants={cardVariants}>
              <AgentWorkflowCard
                wf={wf}
                assigned={wf.id === watchedWorkflowId}
                viewedVersion={viewedVersion}
                onOpen={openBuilder}
                onAssign={assign}
                onUnassign={unassign}
                onClone={setCloneTarget}
                onDelete={handleDelete}
              />
            </motion.div>
          ))}
        </motion.div>
      )}

      <CreateWorkflowModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        agentId={agentId}
        builderBasePath={basePath}
      />

      <CloneWorkflowModal
        workflow={cloneTarget}
        onClose={() => setCloneTarget(null)}
        onCloned={load}
        agentId={agentId}
      />
    </div>
  );
}
