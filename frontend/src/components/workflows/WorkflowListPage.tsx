'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAtomValue, useSetAtom } from 'jotai';
import { motion } from 'framer-motion';
import { GitBranch, Plus, Workflow as WorkflowIcon } from 'lucide-react';

import { cn } from '@/utils/cn';
import CustomButton from '@/components/shared/CustomButton';
import ActionMenu from '@/components/shared/ActionMenu';
import { deleteWorkflowAtom, fetchWorkflowListAtom, workflowsAtom } from '@/atoms/WorkflowAtom';
import { showToast } from '@/utils/toast';
import { handleApiError } from '@/utils/helpers';
import type { WorkflowSummary } from '@/types/workflow';
import CreateWorkflowModal from './CreateWorkflowModal';

const WorkflowListPage: React.FC = () => {
  const router = useRouter();
  const { list, loading } = useAtomValue(workflowsAtom);
  const fetchList = useSetAtom(fetchWorkflowListAtom);
  const remove = useSetAtom(deleteWorkflowAtom);

  const [createOpen, setCreateOpen] = useState(false);

  useEffect(() => {
    fetchList().catch(handleApiError);
  }, [fetchList]);

  const handleDelete = async (wf: WorkflowSummary) => {
    try {
      await remove(wf.id);
      showToast.success('Workflow deleted');
      await fetchList();
    } catch (err) {
      handleApiError(err);
    }
  };

  return (
    <div className="mx-auto h-full max-w-6xl px-6 py-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Workflows</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
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

      {loading && list.length === 0 ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="h-32 animate-pulse rounded-xl border border-border bg-muted/40"
            />
          ))}
        </div>
      ) : list.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-border py-20 text-center">
          <span className="mb-4 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary ring-1 ring-inset ring-primary/20">
            <GitBranch className="h-7 w-7" />
          </span>
          <h2 className="text-lg font-semibold text-foreground">Design your first workflow</h2>
          <p className="mt-1 max-w-sm text-sm text-muted-foreground">
            Build a branching conversation flow on a visual canvas, then assign it to an agent.
          </p>
          <CustomButton
            type="primary"
            className="mt-5"
            icon={<Plus className="h-4 w-4" />}
            onClick={() => setCreateOpen(true)}
          >
            New workflow
          </CustomButton>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {list.map((wf, i) => (
            <motion.div
              key={wf.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2, delay: i * 0.04, ease: 'easeOut' }}
              onClick={() => router.push(`/workflows/${wf.id}`)}
              className="group relative flex cursor-pointer flex-col rounded-xl border border-border bg-card p-4 text-left shadow-sm transition-all hover:-translate-y-px hover:border-primary/40 hover:shadow-md"
            >
              <div className="mb-2 flex items-start justify-between gap-2">
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
              {wf.description && (
                <div className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
                  {wf.description}
                </div>
              )}
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
                  <span className="rounded-full bg-destructive/10 px-2 py-0.5 text-[11px] font-medium text-destructive ring-1 ring-inset ring-destructive/20">
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
