'use client';

import { ActionMenu } from '@/components/shared';
import CustomTable from '@/components/shared/CustomTable';
import type { CustomTableColumn } from '@/types/components';
import type { IntegrationRow } from '@/types/integration';
import { Loader2 } from 'lucide-react';

interface IntegrationsTableProps {
  rows: IntegrationRow[];
  loading?: boolean;
  onEdit: (row: IntegrationRow) => void;
  onDelete: (id: number) => Promise<void>;
}

export default function IntegrationsTable({
  rows,
  loading,
  onEdit,
  onDelete,
}: IntegrationsTableProps) {
  const columns: CustomTableColumn<IntegrationRow>[] = [
    { key: 'name', title: 'Name', dataIndex: 'name' },
    { key: 'account_sid', title: 'Account SID', dataIndex: 'account_sid' },
    { key: 'auth_token', title: 'Auth Token', dataIndex: 'auth_token' },
    { key: 'createdAt', title: 'Created at', dataIndex: 'createdAt' },
    {
      key: 'actions',
      title: '',
      width: 'w-24',
      render: (_value, record) => (
        <ActionMenu
          onEdit={() => onEdit(record)}
          onDelete={() => onDelete(record.id)}
          deleteTitle="Delete Integration"
          deleteDescription="Are you sure you want to delete this integration? This action cannot be undone."
          confirmText="Delete"
        />
      ),
    },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="size-9 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <CustomTable
      columns={columns}
      onRowClick={(record) => onEdit(record)}
      dataSource={rows}
      rowKey="id"
    />
  );
}
