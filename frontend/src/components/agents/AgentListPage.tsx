'use client';

import { deleteAgentAtom } from '@/atoms/AgentsAtom';
import { AgentActionMenu } from '@/components/agents/AgentActionMenu';
import { AgentTypeBadge } from '@/components/agents/AgentTypeBadge';
import { agentsListConfig } from '@/components/agents/agentsListConfig';
import CloneAgentModal from '@/components/agents/CloneAgentModal';
import CreateAgentModal from '@/components/agents/CreateAgentModal';
import AgentReadinessCell from '@/components/agents/readiness/AgentReadinessCell';
import ReadinessDrawer from '@/components/agents/readiness/ReadinessDrawer';
import {
  CustomButton,
  CustomTable,
  FacetFilterBar,
  FacetFilterDrawer,
  PhoneNumberDisplay,
  useFacetedList,
} from '@/components/shared';
import type { ApiAgent } from '@/types/agent';
import type { CustomTableColumn } from '@/types/components';
import { cn } from '@/utils/cn';
import { formatDate } from '@/utils/date';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { useAtom } from 'jotai';
import { Bot, Plus } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useState } from 'react';

const AgentListPage: React.FC = () => {
  const router = useRouter();
  const [, removeAgent] = useAtom(deleteAgentAtom);

  const fl = useFacetedList(agentsListConfig);
  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [cloneTarget, setCloneTarget] = useState<ApiAgent | null>(null);
  const [readinessTarget, setReadinessTarget] = useState<string | null>(null);

  const handleEdit = useCallback(
    (row: ApiAgent) => {
      const type = (row.agent_type ?? 'inbound').toString().toLowerCase();
      if (!row.id) return;
      router.push(`/agents/edit/${type}/${row.id}`);
    },
    [router],
  );

  const handleDelete = useCallback(
    async (agentId: string) => {
      try {
        await removeAgent(agentId);
        showToast.success('Agent deleted successfully');
        const remaining = Math.max(0, fl.total - 1);
        const lastPage = Math.max(1, Math.ceil(remaining / fl.pageSize));
        if (fl.page > lastPage) fl.handlePaginationChange(lastPage, fl.pageSize);
        else fl.refresh();
      } catch (error) {
        handleApiError(error);
      }
    },
    [removeAgent, fl],
  );

  const handleClone = useCallback((row: ApiAgent) => {
    setCloneTarget(row);
  }, []);

  const columns: CustomTableColumn<ApiAgent>[] = [
    {
      key: 'name',
      title: 'Agent',
      dataIndex: 'name',
      sorter: true,
      render: (_value, record) => (
        <div className="flex flex-col gap-0.5">
          <span className="text-body font-medium text-foreground">{record.name}</span>
          {record.description && (
            <span className="max-w-[280px] truncate text-micro text-muted-foreground">
              {record.description}
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'status',
      title: 'Status',
      render: (_value, record) => {
        const hasPhone = record.phone_number && record.phone_number.length > 0;
        return (
          <span className="inline-flex items-center gap-2">
            <span
              className={cn(
                'size-1.5 shrink-0 rounded-full',
                hasPhone ? 'bg-success' : 'bg-muted-foreground/40',
              )}
            />
            <span
              className={cn('text-caption', hasPhone ? 'text-foreground' : 'text-muted-foreground')}
            >
              {hasPhone ? 'Active' : 'Inactive'}
            </span>
          </span>
        );
      },
    },
    {
      key: 'agent_type',
      title: 'Type',
      dataIndex: 'agent_type',
      sorter: true,
      render: (_value, record) => <AgentTypeBadge agentType={record.agent_type} />,
    },
    {
      key: 'readiness',
      title: 'Readiness',
      render: (_value, record) => (
        <AgentReadinessCell
          agentId={record.id}
          readiness={record.readiness}
          onOpen={(agentId) => setReadinessTarget(agentId)}
        />
      ),
    },
    {
      key: 'phone_number',
      title: 'Phone',
      dataIndex: 'phone_number',
      render: (value) => {
        const phones = value as { type: string; no: string }[] | null | undefined;
        if (!phones || phones.length === 0) return <span className="text-muted-foreground">—</span>;
        return (
          <div className="flex flex-col gap-1">
            {phones.map((p) => (
              <PhoneNumberDisplay key={p.no} phoneNumber={p.no} flagSize="sm" />
            ))}
          </div>
        );
      },
    },
    {
      key: 'updated_at',
      title: 'Last Updated',
      dataIndex: 'updated_at',
      sorter: true,
      render: (value) =>
        value ? (
          <span className="text-caption tabular-nums text-muted-foreground">
            {formatDate(value as number)}
          </span>
        ) : (
          <span className="text-muted-foreground">—</span>
        ),
    },
    {
      key: 'actions',
      title: '',
      align: 'right',
      render: (_value, record) => (
        <div className="flex items-center justify-end gap-1">
          <AgentActionMenu
            agentName={record.name}
            onEdit={() => handleEdit(record)}
            onDelete={() => handleDelete(record.id)}
            onClone={() => handleClone(record)}
          />
        </div>
      ),
    },
  ];

  return (
    <div className="animate-page mx-auto flex h-full w-full max-w-6xl flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <p className="mb-3 font-mono text-eyebrow uppercase tracking-[0.34em] text-muted-foreground">
            Build
          </p>
          <div className="flex items-baseline gap-3">
            <h1 className="font-display text-[clamp(2rem,3.4vw,2.75rem)] font-semibold leading-none tracking-[-0.04em] text-foreground">
              Agents
            </h1>
            {fl.total > 0 && (
              <span className="font-mono text-caption tabular-nums text-muted-foreground">
                {fl.total}
              </span>
            )}
          </div>
          <p className="mt-2 text-body text-muted-foreground">Manage your voice agents</p>
        </div>
        <CustomButton
          type="primary"
          icon={<Plus size={15} />}
          className="h-10"
          onClick={() => setModalOpen(true)}
        >
          Create agent
        </CustomButton>
      </div>

      <FacetFilterBar
        fields={fl.tokenFields}
        tokens={fl.tokens}
        onTokensChange={fl.setTokens}
        onClear={fl.clearAll}
        showClear={fl.hasActiveFilters}
        placeholder="Search agents… (e.g. name:hotel)"
        drawerFilterCount={fl.drawerFilterCount}
        onOpenDrawer={() => setFilterDrawerOpen(true)}
      />

      <div className="flex min-h-0 flex-1 flex-col">
        <CustomTable
          columns={columns}
          dataSource={fl.rows}
          rowKey="id"
          loading={fl.listLoading}
          loadingLabel="Loading agents"
          onRowClick={handleEdit}
          onSortChange={fl.handleSortChange}
          initialSort={agentsListConfig.defaultSort ?? undefined}
          pagination={{
            current: fl.page,
            pageSize: fl.pageSize,
            total: fl.total,
            pageSizeOptions: fl.pageSizeOptions,
            onChange: fl.handlePaginationChange,
          }}
          emptyState={
            <div className="flex flex-col items-center gap-5 py-14">
              <span className="inline-flex size-12 items-center justify-center rounded-xl border border-border bg-surface text-muted-foreground">
                <Bot className="size-5" strokeWidth={1.75} />
              </span>
              <div className="text-center">
                <p className="font-display text-heading font-semibold text-foreground">
                  No agents yet
                </p>
                <p className="mt-1.5 text-body text-muted-foreground">
                  Create your first voice agent to get started
                </p>
              </div>
              <CustomButton
                type="primary"
                icon={<Plus size={15} />}
                className="h-10"
                onClick={() => setModalOpen(true)}
              >
                Create agent
              </CustomButton>
            </div>
          }
        />
      </div>

      <FacetFilterDrawer
        open={filterDrawerOpen}
        onClose={() => setFilterDrawerOpen(false)}
        description="Filter agents by type and status."
        sections={agentsListConfig.facetSections}
        value={fl.facetSelections}
        facets={fl.facets}
        facetsLoading={fl.facetsLoading}
        onApply={fl.applyDrawer}
      />

      <CreateAgentModal open={modalOpen} onClose={() => setModalOpen(false)} />

      <CloneAgentModal
        agent={cloneTarget}
        onClose={() => setCloneTarget(null)}
        onCloned={() => fl.refresh()}
      />

      <ReadinessDrawer
        open={readinessTarget !== null}
        onClose={() => setReadinessTarget(null)}
        agentId={readinessTarget}
        trigger="list_page"
      />
    </div>
  );
};

export default AgentListPage;
