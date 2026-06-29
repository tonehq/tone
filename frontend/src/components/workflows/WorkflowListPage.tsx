'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAtomValue, useSetAtom } from 'jotai';
import { motion } from 'framer-motion';
import {
  CheckCircle2,
  Clock,
  PencilRuler,
  Plus,
  RefreshCw,
  SearchX,
  TriangleAlert,
  Users,
  Workflow as WorkflowIcon,
} from 'lucide-react';

import { cn } from '@/utils/cn';
import CustomButton from '@/components/shared/CustomButton';
import TokenSearchBar from '@/components/shared/TokenSearchBar';
import ActionMenu from '@/components/shared/ActionMenu';
import { deleteWorkflowAtom, fetchWorkflowListAtom, workflowsAtom } from '@/atoms/WorkflowAtom';
import { showToast } from '@/utils/toast';
import { handleApiError } from '@/utils/helpers';
import { formatRelative } from '@/utils/date';
import type { SearchToken, TokenSearchField } from '@/types/components';
import type { WorkflowSummary } from '@/types/workflow';
import CreateWorkflowModal from './CreateWorkflowModal';
import WorkflowEmptyState from './WorkflowEmptyState';

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

// ── status pill ───────────────────────────────────────────────────────────────
const StatusPill: React.FC<{ status: WorkflowSummary['status'] }> = ({ status }) => {
  const published = status === 'published';
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset',
        published
          ? 'bg-emerald-500/10 text-emerald-600 ring-emerald-500/20 dark:text-emerald-300'
          : 'bg-amber-500/10 text-amber-600 ring-amber-500/20 dark:text-amber-300',
      )}
    >
      <span
        className={cn('h-1.5 w-1.5 rounded-full', published ? 'bg-emerald-500' : 'bg-amber-500')}
      />
      {published ? 'Published' : 'Draft'}
    </span>
  );
};

// ── one workflow card ─────────────────────────────────────────────────────────
interface CardProps {
  wf: WorkflowSummary;
  index: number;
  onOpen: (id: string) => void;
  onDelete: (wf: WorkflowSummary) => void;
}

const WorkflowCard: React.FC<CardProps> = ({ wf, index, onOpen, onDelete }) => {
  const published = wf.status === 'published';
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, delay: Math.min(index, 10) * 0.035, ease: 'easeOut' }}
      role="button"
      tabIndex={0}
      aria-label={`Open workflow ${wf.name}`}
      onClick={() => onOpen(wf.id)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onOpen(wf.id);
        }
      }}
      className="group relative flex cursor-pointer flex-col overflow-hidden rounded-xl border border-border bg-card text-left outline-none transition-all duration-200 hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5 focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background"
    >
      {/* status accent rail */}
      <span
        aria-hidden
        className={cn(
          'absolute inset-x-0 top-0 h-[2.5px] opacity-70 transition-opacity group-hover:opacity-100',
          published
            ? 'bg-gradient-to-r from-emerald-500/80 via-emerald-400/60 to-transparent'
            : 'bg-gradient-to-r from-amber-500/80 via-amber-400/60 to-transparent',
        )}
      />

      <div className="flex flex-1 flex-col p-4">
        {/* header */}
        <div className="mb-3 flex items-start justify-between gap-2">
          <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-600 ring-1 ring-inset ring-indigo-500/20 dark:text-indigo-300">
            <WorkflowIcon className="h-5 w-5" strokeWidth={1.75} />
          </span>
          <div
            className="opacity-60 transition-opacity group-hover:opacity-100"
            onClick={(e) => e.stopPropagation()}
          >
            <ActionMenu
              itemName={wf.name}
              onEdit={() => onOpen(wf.id)}
              onDelete={() => Promise.resolve(onDelete(wf))}
              deleteDescription={`This permanently removes "${wf.name}". Workflows assigned to an agent must be unassigned first.`}
            />
          </div>
        </div>

        {/* title + description */}
        <h3 className="truncate text-[15px] font-semibold tracking-tight text-foreground">
          {wf.name}
        </h3>
        <p className="mt-1 line-clamp-2 min-h-[2.25rem] text-xs leading-relaxed text-muted-foreground">
          {wf.description || 'No description'}
        </p>

        {/* meta pills */}
        <div className="mt-3.5 flex flex-wrap items-center gap-1.5">
          <StatusPill status={wf.status} />
          <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
            <Users className="h-3 w-3" />
            {wf.agents_using} agent{wf.agents_using === 1 ? '' : 's'}
          </span>
          {wf.is_valid ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
              <CheckCircle2 className="h-3 w-3 text-emerald-500" />
              Valid
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full bg-destructive/10 px-2 py-0.5 text-[11px] font-medium text-destructive ring-1 ring-inset ring-destructive/20">
              <TriangleAlert className="h-3 w-3" />
              Has issues
            </span>
          )}
        </div>
      </div>

      {/* footer */}
      <div className="flex items-center justify-between border-t border-border/60 bg-muted/30 px-4 py-2">
        <span className="inline-flex items-center gap-1.5 font-mono text-[11px] text-muted-foreground">
          <Clock className="h-3 w-3" />
          {wf.updated_at ? `Updated ${formatRelative(wf.updated_at)}` : 'Not yet edited'}
        </span>
        <span className="text-[11px] font-medium text-primary opacity-0 transition-opacity group-hover:opacity-100">
          Open →
        </span>
      </div>
    </motion.div>
  );
};

// ── page ──────────────────────────────────────────────────────────────────────
const WorkflowListPage: React.FC = () => {
  const router = useRouter();
  const { list, loading } = useAtomValue(workflowsAtom);
  const fetchList = useSetAtom(fetchWorkflowListAtom);
  const remove = useSetAtom(deleteWorkflowAtom);

  const [createOpen, setCreateOpen] = useState(false);
  const [errored, setErrored] = useState(false);
  const [loadedOnce, setLoadedOnce] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [tokens, setTokens] = useState<SearchToken[]>([]);

  const load = useCallback(
    (silent = false) => {
      setErrored(false);
      setRefreshing(true);
      fetchList()
        .catch((err) => {
          setErrored(true);
          if (!silent) handleApiError(err);
        })
        .finally(() => {
          setLoadedOnce(true);
          setRefreshing(false);
        });
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

      {/* toolbar — only once there is at least one workflow */}
      {!showSkeleton && !isTrulyEmpty && !errored && (
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <TokenSearchBar
            fields={SEARCH_FIELDS}
            value={tokens}
            onChange={setTokens}
            onClear={() => setTokens([])}
            placeholder="Filter workflows… (e.g. status:draft)"
            className="w-full sm:max-w-xl"
          />

          <div className="flex items-center gap-3">
            <span className="hidden whitespace-nowrap font-mono text-xs text-muted-foreground sm:inline">
              {tokens.length ? `${filtered.length} of ${list.length}` : `${list.length} total`}
            </span>
            <CustomButton
              type="default"
              size="icon-sm"
              aria-label="Refresh workflows"
              loading={refreshing}
              onClick={() => load()}
              icon={<RefreshCw className="h-4 w-4" />}
            />
          </div>
        </div>
      )}

      {/* body */}
      {showSkeleton ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="h-[180px] animate-pulse rounded-xl border border-border bg-muted/40"
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
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">
          {filtered.map((wf, i) => (
            <WorkflowCard key={wf.id} wf={wf} index={i} onOpen={open} onDelete={handleDelete} />
          ))}
        </div>
      )}

      <CreateWorkflowModal open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  );
};

export default WorkflowListPage;
