'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAtomValue, useSetAtom } from 'jotai';
import { motion } from 'framer-motion';
import { PencilRuler, Plus, RefreshCw, SearchX, TriangleAlert } from 'lucide-react';

import CustomButton from '@/components/shared/CustomButton';
import TokenSearchBar from '@/components/shared/TokenSearchBar';
import { deleteWorkflowAtom, fetchWorkflowListAtom, workflowsAtom } from '@/atoms/WorkflowAtom';
import { showToast } from '@/utils/toast';
import { handleApiError } from '@/utils/helpers';
import type { SearchToken, TokenSearchField } from '@/types/components';
import type { WorkflowSummary } from '@/types/workflow';
import CreateWorkflowModal from './CreateWorkflowModal';
import WorkflowEmptyState from './WorkflowEmptyState';
import WorkflowCard from './WorkflowCard';
import WorkflowCardSkeleton from './WorkflowCardSkeleton';

// Vercel-style `field:value` search fields (mirrors the Agents list search).
const SEARCH_FIELDS: TokenSearchField[] = [
  { key: 'name', label: 'Name', type: 'text' },
  {
    key: 'status',
    label: 'Status',
    type: 'enum',
    fetchValues: async () => ['draft', 'published'],
    formatValue: (v) => (v === 'published' ? 'Published' : 'Draft'),
  },
];

const WorkflowListPage: React.FC = () => {
  const router = useRouter();
  const { list, loading } = useAtomValue(workflowsAtom);
  const fetchList = useSetAtom(fetchWorkflowListAtom);
  const remove = useSetAtom(deleteWorkflowAtom);

  const [createOpen, setCreateOpen] = useState(false);
  const [errored, setErrored] = useState(false);
  const [loadedOnce, setLoadedOnce] = useState(false);
  const [tokens, setTokens] = useState<SearchToken[]>([]);

  const load = useCallback(
    (silent = false) => {
      setErrored(false);
      fetchList()
        .catch((err) => {
          setErrored(true);
          if (!silent) handleApiError(err);
        })
        .finally(() => setLoadedOnce(true));
    },
    [fetchList],
  );

  useEffect(() => {
    load(true);
  }, [load]);

  const open = useCallback((id: string) => router.push(`/workflows/${id}`), [router]);

  const handleDelete = useCallback(
    async (wf: WorkflowSummary) => {
      try {
        await remove(wf.id);
        showToast.success('Workflow deleted');
        load(true);
      } catch (err) {
        handleApiError(err);
      }
    },
    [remove, load],
  );

  const filtered = useMemo(() => {
    const statusVals = tokens.filter((t) => t.field === 'status').map((t) => t.value);
    const textVals = tokens
      .filter((t) => t.field === 'name')
      .map((t) => t.value.trim().toLowerCase())
      .filter(Boolean);
    return list.filter((w) => {
      if (statusVals.length && !statusVals.includes(w.status)) return false;
      if (textVals.length) {
        const hay = `${w.name} ${w.description ?? ''}`.toLowerCase();
        if (!textVals.every((t) => hay.includes(t))) return false;
      }
      return true;
    });
  }, [list, tokens]);

  const showSkeleton = (loading || !loadedOnce) && list.length === 0 && !errored;
  const isTrulyEmpty = loadedOnce && !errored && list.length === 0;
  const showErrorScreen = errored && list.length === 0;
  // Keep the toolbar (search + refresh) visible during the initial skeleton load too;
  // only hide it once we know there are genuinely no workflows and no active filters.
  const showToolbar = !showErrorScreen && (showSkeleton || list.length > 0 || tokens.length > 0);

  return (
    <div className="relative h-full">
      {/* atmospheric backdrop */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 opacity-[0.55]"
        style={{
          backgroundImage: 'radial-gradient(hsl(var(--border)) 1px, transparent 1px)',
          backgroundSize: '22px 22px',
          maskImage: 'radial-gradient(70% 55% at 50% 0%, black, transparent 75%)',
          WebkitMaskImage: 'radial-gradient(70% 55% at 50% 0%, black, transparent 75%)',
        }}
      />

      {/* header */}
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">Workflows</h1>
            {list.length > 0 && (
              <span className="rounded-full bg-muted px-2 py-0.5 font-mono text-xs text-muted-foreground">
                {list.length}
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            Visual conversation pathways you can assign to any agent.
          </p>
        </div>
        <CustomButton
          type="primary"
          icon={<Plus className="h-4 w-4" />}
          onClick={() => setCreateOpen(true)}
        >
          New workflow
        </CustomButton>
      </div>

      {/* toolbar — visible during load, and whenever there is data or an active filter */}
      {showToolbar && (
        <div className="mb-5">
          <TokenSearchBar
            fields={SEARCH_FIELDS}
            value={tokens}
            onChange={setTokens}
            onClear={() => setTokens([])}
            placeholder="Filter workflows… (e.g. status:draft)"
            className="w-full sm:max-w-xl"
          />
        </div>
      )}

      {/* body */}
      {showSkeleton ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <WorkflowCardSkeleton key={i} />
          ))}
        </div>
      ) : showErrorScreen ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-border py-20 text-center">
          <span className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-destructive/10 text-destructive ring-1 ring-inset ring-destructive/20">
            <TriangleAlert className="h-6 w-6" />
          </span>
          <h2 className="text-base font-semibold text-foreground">Couldn’t load workflows</h2>
          <p className="mt-1 max-w-sm text-sm text-muted-foreground">
            Something went wrong while fetching your workflows. Check your connection and try again.
          </p>
          <CustomButton
            type="default"
            className="mt-5"
            icon={<RefreshCw className="h-4 w-4" />}
            onClick={() => load()}
          >
            Retry
          </CustomButton>
        </div>
      ) : isTrulyEmpty ? (
        <WorkflowEmptyState onCreate={() => setCreateOpen(true)} />
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-border py-20 text-center">
          <span className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-muted text-muted-foreground ring-1 ring-inset ring-border">
            <SearchX className="h-6 w-6" />
          </span>
          <h2 className="text-base font-semibold text-foreground">No matching workflows</h2>
          <p className="mt-1 max-w-sm text-sm text-muted-foreground">
            No workflows match your current search and filters.
          </p>
          <CustomButton
            type="default"
            className="mt-5"
            icon={<PencilRuler className="h-4 w-4" />}
            onClick={() => setTokens([])}
          >
            Clear filters
          </CustomButton>
        </div>
      ) : (
        <motion.div
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3"
          initial="hidden"
          animate="visible"
          variants={{
            hidden: {},
            visible: { transition: { staggerChildren: 0.04, delayChildren: 0.05 } },
          }}
        >
          {filtered.map((wf) => (
            <motion.div
              key={wf.id}
              className="h-full"
              variants={{
                hidden: { opacity: 0, y: 12 },
                visible: { opacity: 1, y: 0, transition: { duration: 0.35 } },
              }}
            >
              <WorkflowCard wf={wf} onOpen={open} onDelete={handleDelete} />
            </motion.div>
          ))}
        </motion.div>
      )}

      <CreateWorkflowModal open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  );
};

export default WorkflowListPage;
