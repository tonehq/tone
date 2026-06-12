'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAtomValue, useSetAtom } from 'jotai';
import { motion } from 'framer-motion';
import { Plus, RefreshCw, TriangleAlert, Workflow as WorkflowIcon } from 'lucide-react';

import { cn } from '@/utils/cn';
import CustomButton from '@/components/shared/CustomButton';
import ActionMenu from '@/components/shared/ActionMenu';
import { deleteWorkflowAtom, fetchWorkflowListAtom, workflowsAtom } from '@/atoms/WorkflowAtom';
import { showToast } from '@/utils/toast';
import { handleApiError } from '@/utils/helpers';
import type { WorkflowSummary } from '@/types/workflow';
import CreateWorkflowModal from './CreateWorkflowModal';
import WorkflowEmptyState from './WorkflowEmptyState';

const WorkflowListPage: React.FC = () => {
  const router = useRouter();
  const { list, loading } = useAtomValue(workflowsAtom);
  const fetchList = useSetAtom(fetchWorkflowListAtom);
  const remove = useSetAtom(deleteWorkflowAtom);

  const [createOpen, setCreateOpen] = useState(false);
  const [errored, setErrored] = useState(false);
  const [loadedOnce, setLoadedOnce] = useState(false);

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

  const handleDelete = async (wf: WorkflowSummary) => {
    try {
      await remove(wf.id);
      showToast.success('Workflow deleted');
      load(true);
    } catch (err) {
      handleApiError(err);
    }
  };

  const showSkeleton = (loading || !loadedOnce) && list.length === 0 && !errored;

  return (
    <div className="mx-auto h-full max-w-6xl px-6 py-8">
      <div className="mb-7 flex items-end justify-between gap-4">
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

      {showSkeleton ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="h-36 animate-pulse rounded-xl border border-border bg-muted/40"
            />
          ))}
        </div>
      ) : errored && list.length === 0 ? (
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
      ) : list.length === 0 ? (
        <WorkflowEmptyState onCreate={() => setCreateOpen(true)} />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {list.map((wf, i) => (
            <motion.div
              key={wf.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2, delay: Math.min(i, 8) * 0.04, ease: 'easeOut' }}
              role="button"
              tabIndex={0}
              onClick={() => router.push(`/workflows/${wf.id}`)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  router.push(`/workflows/${wf.id}`);
                }
              }}
              className="group relative flex cursor-pointer flex-col rounded-xl border border-border bg-card p-4 text-left shadow-sm outline-none transition-all hover:-translate-y-px hover:border-primary/40 hover:shadow-md focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            >
              <span
                aria-hidden
                className="absolute inset-x-0 top-0 h-[3px] rounded-t-xl bg-gradient-to-r from-indigo-500/60 via-violet-500/50 to-transparent opacity-0 transition-opacity group-hover:opacity-100"
              />
              <div className="mb-2.5 flex items-start justify-between gap-2">
                <span className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-600 ring-1 ring-inset ring-indigo-500/20 dark:text-indigo-300">
                  <WorkflowIcon className="h-5 w-5" />
                </span>
                <div onClick={(e) => e.stopPropagation()}>
                  <ActionMenu
                    itemName={wf.name}
                    onEdit={() => router.push(`/workflows/${wf.id}`)}
                    onDelete={() => handleDelete(wf)}
                    deleteDescription={`This permanently removes "${wf.name}". Workflows assigned to an agent must be unassigned first.`}
                  />
                </div>
              </div>
              <div className="truncate text-sm font-semibold text-foreground">{wf.name}</div>
              <div className="mt-0.5 line-clamp-2 min-h-[2rem] text-xs text-muted-foreground">
                {wf.description || 'No description'}
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span
                  className={cn(
                    'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset',
                    wf.status === 'published'
                      ? 'bg-emerald-500/10 text-emerald-600 ring-emerald-500/20 dark:text-emerald-300'
                      : 'bg-amber-500/10 text-amber-600 ring-amber-500/20 dark:text-amber-300',
                  )}
                >
                  <span
                    className={cn(
                      'h-1.5 w-1.5 rounded-full',
                      wf.status === 'published' ? 'bg-emerald-500' : 'bg-amber-500',
                    )}
                  />
                  {wf.status === 'published' ? 'Published' : 'Draft'}
                </span>
                <span className="rounded-full bg-muted px-2 py-0.5 font-mono text-[11px] text-muted-foreground">
                  {wf.agents_using} agent{wf.agents_using === 1 ? '' : 's'}
                </span>
                {!wf.is_valid && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-destructive/10 px-2 py-0.5 text-[11px] font-medium text-destructive ring-1 ring-inset ring-destructive/20">
                    <TriangleAlert className="h-3 w-3" />
                    Has issues
                  </span>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      )}

      <CreateWorkflowModal open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  );
};

export default WorkflowListPage;
