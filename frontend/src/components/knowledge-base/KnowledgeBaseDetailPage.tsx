'use client';

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, ClipboardCheck, FileText, ListChecks, Settings2 } from 'lucide-react';
import Link from 'next/link';

import IngestionConfigsTab from '@/components/knowledge-base/IngestionConfigsTab';
import IngestionRunsTab from '@/components/knowledge-base/IngestionRunsTab';
import KnowledgeBaseOverview from '@/components/knowledge-base/KnowledgeBaseOverview';
import ManageEvalsTab from '@/components/knowledge-base/ManageEvalsTab';
import { CustomButton, CustomTab, type TabItem } from '@/components/shared';
import { useAgents } from '@/hooks/useAgents';
import { knowledgeBaseApi, KNOWLEDGE_BASE_QUERY_KEY } from '@/lib/api/knowledge-base';
import type { AgentDropdownItem } from '@/types/agent';
import type { KnowledgeBaseDocument } from '@/types/knowledgeBase';

interface KnowledgeBaseDetailPageProps {
  uploadId: string;
}

// Detail page for one KB document. Uses the list endpoint filtered by
// `agent_id=` unset + id (there is no `GET /knowledge-base/{id}` endpoint
// today) — we fetch the first page and pick the matching row. Cheap because
// the list is small in practice; swap for a dedicated GET if that changes.
export default function KnowledgeBaseDetailPage({ uploadId }: KnowledgeBaseDetailPageProps) {
  // The agent list (for name resolution) comes from the shared TanStack Query
  // hook, so a deep link into this page fetches + caches it the same way the KB
  // list page does — no ref-guarded atom priming needed.
  const { data: agentList = [] } = useAgents();

  const { data, isLoading, isError } = useQuery({
    queryKey: [KNOWLEDGE_BASE_QUERY_KEY, 'detail', uploadId],
    queryFn: () => knowledgeBaseApi.list({ page: 1, page_size: 100 }),
  });

  const doc: KnowledgeBaseDocument | null = useMemo(
    () => data?.items.find((d) => d.id === uploadId) ?? null,
    [data, uploadId],
  );

  const agentName = useMemo(() => {
    if (!doc?.agent_id) return null;
    const found = agentList.find(
      (a: AgentDropdownItem) => a.uuid === doc.agent_id || String(a.id) === doc.agent_id,
    );
    return found?.name ?? 'Unknown agent';
  }, [doc, agentList]);

  const tabs: TabItem[] = useMemo(
    () => [
      {
        key: 'overview',
        label: 'Overview',
        icon: <FileText className="size-4" />,
        children: doc ? (
          <div className="max-w-2xl py-4">
            <KnowledgeBaseOverview doc={doc} agentName={agentName} />
          </div>
        ) : (
          <div className="py-10 text-center text-sm text-muted-foreground">
            {isLoading ? 'Loading…' : 'Document not found.'}
          </div>
        ),
      },
      {
        key: 'ingestion-runs',
        label: 'Ingestion runs',
        icon: <ListChecks className="size-4" />,
        // The runs tab derives the active-run id from the runs list itself
        // (via `is_active`), so no prop is required here.
        children: <IngestionRunsTab uploadId={uploadId} />,
      },
      {
        key: 'manage-evals',
        label: 'Manage evals',
        icon: <ClipboardCheck className="size-4" />,
        children: <ManageEvalsTab uploadId={uploadId} />,
      },
      {
        key: 'ingestion-configs',
        label: 'Ingestion configs',
        icon: <Settings2 className="size-4" />,
        children: <IngestionConfigsTab />,
      },
    ],
    [doc, isLoading, agentName, uploadId],
  );

  return (
    <div className="animate-page flex h-full min-h-0 flex-col gap-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3">
          <Link href="/knowledge-base" className="mt-1">
            <CustomButton type="text" size="icon-xs" aria-label="Back to knowledge base list">
              <ArrowLeft className="size-4" />
            </CustomButton>
          </Link>
          <div className="min-w-0">
            <h1 className="truncate font-display text-[1.75rem] font-semibold tracking-[-0.03em] text-foreground">
              {doc?.file_name ?? 'Knowledge base document'}
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              View document details and its ingestion pipeline runs.
            </p>
          </div>
        </div>
      </div>

      {isError && (
        <div className="rounded-xl border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          Failed to load document.
        </div>
      )}

      <CustomTab items={tabs} defaultActiveKey="overview" className="min-h-0 flex-1" />
    </div>
  );
}
