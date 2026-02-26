'use client';

import agentsAtom, { deleteAgentAtom, fetchAgentList } from '@/atoms/AgentsAtom';
import { AgentActionMenu } from '@/components/agents/AgentActionMenu';
import { AgentTypeBadge } from '@/components/agents/AgentTypeBadge';
import CreateAgentModal from '@/components/agents/CreateAgentModal';
import { CustomButton, CustomTable } from '@/components/shared';
import type { ApiAgent } from '@/types/agent';
import type { CustomTableColumn } from '@/types/components';
import { useNotification } from '@/utils/notification';
import dayjs from 'dayjs';
import { useAtom } from 'jotai';
import { Plus } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';

const AgentListPage: React.FC = () => {
  const router = useRouter();
  const [data] = useAtom(agentsAtom);
  const [, fetAgentsList] = useAtom(fetchAgentList);
  const [, removeAgent] = useAtom(deleteAgentAtom);
  const [loader, setLoader] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const { notify, contextHolder } = useNotification();

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
        notify.success('Agent Deleted', 'Agent deleted successfully');
      } catch {
        notify.error('Delete Failed', 'Failed to delete agent. Please try again.');
      }
    },
    [removeAgent, notify],
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
      title: 'Agent Name',
      dataIndex: 'name',
      sorter: true,
    },
    {
      key: 'phone_number',
      title: 'Phone Number',
      dataIndex: 'phone_number',
      render: (value) => (value as string) || '-',
    },
    {
      key: 'updated_at',
      title: 'Last Edited',
      dataIndex: 'updated_at',
      sorter: true,
      render: (value) => (value ? dayjs.unix(value as number).format('DD MMM YYYY, HH:mm') : '-'),
    },
    {
      key: 'agent_type',
      title: 'Agent Type',
      dataIndex: 'agent_type',
      render: (_value, record) => <AgentTypeBadge agentType={record.agent_type} />,
    },
    {
      key: 'actions',
      title: '',
      align: 'right',
      render: (_value, record) => (
        <AgentActionMenu
          onEdit={() => handleEdit(record)}
          onDelete={() => handleDelete(record.id)}
        />
      ),
    },
  ];

  return (
    <div className="h-full p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-foreground">Agents</h1>
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
        pagination={{ current: 1, pageSize: 10, pageSizeOptions: [10, 20, 50] }}
        emptyState={
          <div className="flex flex-col items-center gap-3">
            <p className="text-muted-foreground">No agents yet</p>
            <CustomButton type="primary" icon={<Plus />} onClick={() => setModalOpen(true)}>
              Create your first agent
            </CustomButton>
          </div>
        }
      />

      <CreateAgentModal open={modalOpen} onClose={() => setModalOpen(false)} />
      {contextHolder}
    </div>
  );
};

export default AgentListPage;
