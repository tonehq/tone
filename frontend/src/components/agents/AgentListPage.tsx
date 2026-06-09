'use client';

import { deleteAgentAtom, fetchPaginatedAgentList, paginatedAgentsAtom } from '@/atoms/AgentsAtom';
import { AgentActionMenu } from '@/components/agents/AgentActionMenu';
import { AgentTypeBadge } from '@/components/agents/AgentTypeBadge';
import CreateAgentModal from '@/components/agents/CreateAgentModal';
import { PageHeader } from '@/components/layout/page-header';
import { CustomButton, CustomTable, PhoneNumberDisplay } from '@/components/shared';
import SearchBar from '@/components/shared/SearchBar';
import SelectInput from '@/components/shared/SelectInput';
import { Badge } from '@/components/ui/badge';
import { AGENT_TYPE_OPTIONS } from '@/lib/constants/filters';
import type { AgentDirection, ApiAgent, ListAgentsParams } from '@/types/agent';
import type { CustomTableColumn, CustomTableSortState } from '@/types/components';
import { formatDate } from '@/utils/date';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { useAtom } from 'jotai';
import { Bot, Plus } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

const AgentListPage: React.FC = () => {
  const router = useRouter();
  const [data] = useAtom(paginatedAgentsAtom);
  const [, fetchList] = useAtom(fetchPaginatedAgentList);
  const [, removeAgent] = useAtom(deleteAgentAtom);

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState<string | undefined>(undefined);
  const [agentTypeFilter, setAgentTypeFilter] = useState<string>('all');
  const [modalOpen, setModalOpen] = useState(false);

  const params = useMemo<ListAgentsParams>(
    () => ({
      page,
      page_size: pageSize,
      search: search.trim() || undefined,
      sort_by: sortBy,
      agent_type: agentTypeFilter === 'all' ? undefined : (agentTypeFilter as AgentDirection),
    }),
    [page, pageSize, search, sortBy, agentTypeFilter],
  );

  const refresh = useCallback(
    async (overrides: ListAgentsParams = {}) => {
      try {
        await fetchList({ ...params, ...overrides });
      } catch (error) {
        handleApiError(error);
      }
    },
    [fetchList, params],
  );

  useEffect(() => {
    refresh();
  }, [refresh]);

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
        const remaining = Math.max(0, data.total - 1);
        const lastPage = Math.max(1, Math.ceil(remaining / pageSize));
        const nextPage = Math.min(page, lastPage);
        if (nextPage !== page) setPage(nextPage);
        else await refresh();
      } catch (error) {
        handleApiError(error);
      }
    },
    [removeAgent, data.total, pageSize, page, refresh],
  );

  const handleSearchChange = useCallback((value: string) => {
    setSearch(value);
    setPage(1);
  }, []);

  const handleAgentTypeFilter = useCallback((value: string) => {
    setAgentTypeFilter(value);
    setPage(1);
  }, []);

  const handleSortChange = useCallback((sort: CustomTableSortState | null) => {
    setSortBy(sort ? `${sort.order === 'desc' ? '-' : ''}${sort.field}` : undefined);
    setPage(1);
  }, []);

  const handlePaginationChange = useCallback((nextPage: number, nextPageSize: number) => {
    setPage(nextPage);
    setPageSize(nextPageSize);
  }, []);

  const columns: CustomTableColumn<ApiAgent>[] = [
    {
      key: 'name',
      title: 'Agent',
      dataIndex: 'name',
      sorter: true,
      render: (_value, record) => (
        <div className="flex flex-col gap-0.5">
          <span className="font-semibold text-foreground">{record.name}</span>
          {record.description && (
            <span className="max-w-[280px] truncate text-xs text-muted-foreground">
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
        return hasPhone ? (
          <Badge className="gap-1.5 border-transparent bg-amber-400/15 text-amber-600 hover:bg-amber-400/15 dark:text-amber-500">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400/70" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-amber-400" />
            </span>
            Active
          </Badge>
        ) : (
          <Badge className="border-transparent bg-muted text-muted-foreground hover:bg-muted">
            Inactive
          </Badge>
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
          <span className="text-sm text-muted-foreground">{formatDate(value as number)}</span>
        ) : (
          <span className="text-muted-foreground">—</span>
        ),
    },
    {
      key: 'actions',
      title: '',
      align: 'right',
      render: (_value, record) => (
        <AgentActionMenu
          agentName={record.name}
          onEdit={() => handleEdit(record)}
          onDelete={() => handleDelete(record.id)}
        />
      ),
    },
  ];

  return (
    <div className="animate-page flex h-full flex-col gap-6">
      <PageHeader
        kicker={data.total > 0 ? `Agents · ${data.total}` : 'Agents'}
        title="Agents."
        description="Manage your AI voice agents."
        actions={
          <CustomButton type="primary" icon={<Plus />} onClick={() => setModalOpen(true)}>
            Create Agent
          </CustomButton>
        }
      />

      <div className="flex flex-wrap items-center gap-3">
        <SearchBar
          placeholder="Search agents..."
          value={search}
          onSearch={handleSearchChange}
          debounceMs={400}
          containerClassName="max-w-xs flex-1"
        />
        <SelectInput
          name="agent-type-filter"
          options={AGENT_TYPE_OPTIONS}
          value={agentTypeFilter}
          onValueChange={handleAgentTypeFilter}
          placeholder="All types"
          size="sm"
          triggerClassName="min-w-[160px]"
        />
      </div>

      <div className="flex min-h-0 flex-1 flex-col">
        <CustomTable
          columns={columns}
          dataSource={data.items}
          rowKey="id"
          loading={data.loading}
          onRowClick={handleEdit}
          onSortChange={handleSortChange}
          pagination={{
            current: page,
            pageSize,
            total: data.total,
            pageSizeOptions: PAGE_SIZE_OPTIONS,
            onChange: handlePaginationChange,
          }}
          emptyState={
            <div className="flex flex-col items-center gap-4 py-8">
              <div className="flex size-12 items-center justify-center rounded-lg border border-border bg-background">
                <Bot className="size-6 text-foreground" strokeWidth={1.75} />
              </div>
              <div className="text-center">
                <p className="font-semibold text-foreground">No agents yet</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Create your first voice agent to get started
                </p>
              </div>
              <CustomButton type="primary" icon={<Plus />} onClick={() => setModalOpen(true)}>
                Create Agent
              </CustomButton>
            </div>
          }
        />
      </div>

      <CreateAgentModal open={modalOpen} onClose={() => setModalOpen(false)} />
    </div>
  );
};

export default AgentListPage;
