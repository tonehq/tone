'use client';

import agentsAtom, { deleteAgentAtom, fetchAgentList } from '@/atoms/AgentsAtom';
import { AgentActionMenu } from '@/components/agents/AgentActionMenu';
import { AgentTypeBadge } from '@/components/agents/AgentTypeBadge';
import CreateAgentModal from '@/components/agents/CreateAgentModal';
import { CustomButton, CustomTable } from '@/components/shared';
import { Badge } from '@/components/ui/badge';
import type { ApiAgent } from '@/types/agent';
import type { CustomTableColumn } from '@/types/components';
import { formatDate } from '@/utils/date';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { useAtom } from 'jotai';
import { Bot, Plus } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';

const AgentListPage: React.FC = () => {
  const router = useRouter();
  const [data] = useAtom(agentsAtom);
  const [, fetAgentsList] = useAtom(fetchAgentList);
  const [, removeAgent] = useAtom(deleteAgentAtom);
  const [loader, setLoader] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);

  const hasFetchedRef = useRef(false);

  const handleEdit = useCallback(
    (row: ApiAgent) => {
      const type = (row.agent_type ?? 'inbound').toString().toLowerCase();
      if (!row.id) return;
      router.push(`/agents/edit/${type}/${row.id}`);
    },
    [router],
  );

  const handleDelete = useCallback(
    async (agentId: number) => {
      try {
        await removeAgent(agentId);
        showToast.success('Agent deleted successfully');
      } catch (error) {
        handleApiError(error);
      }
    },
    [removeAgent],
  );

  useEffect(() => {
    if (hasFetchedRef.current) return;
    hasFetchedRef.current = true;

    const init = async () => {
      setLoader(true);
      try {
        await fetAgentsList();
      } catch (err) {
        console.error(err);
      } finally {
        setLoader(false);
      }
    };

    init();
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
          <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-900/30 dark:text-emerald-400">
            Active
          </Badge>
        ) : (
          <Badge className="bg-amber-100 text-amber-700 hover:bg-amber-100 dark:bg-amber-900/30 dark:text-amber-400">
            Inactive
          </Badge>
        );
      },
    },
    {
      key: 'agent_type',
      title: 'Type',
      dataIndex: 'agent_type',
      render: (_value, record) => <AgentTypeBadge agentType={record.agent_type} />,
    },
    {
      key: 'phone_number',
      title: 'Phone',
      dataIndex: 'phone_number',
      render: (value) => {
        const phones = value as { type: string; no: string }[] | null | undefined;
        if (!phones || phones.length === 0) return <span className="text-muted-foreground">—</span>;
        return <span className="text-sm">{phones.map((p) => p.no).join(', ')}</span>;
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
    <div className="flex h-full flex-col p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">Agents</h1>
            {data.agentList.length > 0 && (
              <Badge variant="secondary" className="text-xs tabular-nums">
                {data.agentList.length}
              </Badge>
            )}
          </div>
          <p className="mt-1 text-sm text-muted-foreground">Manage your voice agents</p>
        </div>
        <CustomButton type="primary" icon={<Plus />} onClick={() => setModalOpen(true)}>
          Create Agent
        </CustomButton>
      </div>

      <CustomTable
        columns={columns}
        dataSource={data.agentList}
        rowKey="id"
        loading={loader}
        onRowClick={handleEdit}
        searchable
        searchPlaceholder="Search agents..."
        emptyState={
          <div className="flex flex-col items-center gap-4 py-8">
            <div className="flex size-12 items-center justify-center rounded-xl bg-muted">
              <Bot className="size-6 text-muted-foreground" />
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

      <CreateAgentModal open={modalOpen} onClose={() => setModalOpen(false)} />
    </div>
  );
};

export default AgentListPage;
