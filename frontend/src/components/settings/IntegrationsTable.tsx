'use client';

import { CustomButton } from '@/components/shared';
import CustomTable from '@/components/shared/CustomTable';
import type { CustomTableColumn } from '@/types/components';
import type { IntegrationRow } from '@/types/integration';
import { Loader2, Pencil, Trash2 } from 'lucide-react';
import { useState } from 'react';

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
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const handleDelete = async (id: number) => {
    setDeletingId(id);
    try {
      await onDelete(id);
    } finally {
      setDeletingId(null);
    }
  };

  const columns: CustomTableColumn<IntegrationRow>[] = [
    { key: 'name', title: 'Name', dataIndex: 'name' },
    { key: 'account_sid', title: 'Account SID', dataIndex: 'account_sid' },
    { key: 'auth_token', title: 'Auth Token', dataIndex: 'auth_token' },
    { key: 'createdAt', title: 'Created at', dataIndex: 'createdAt' },
    {
      key: 'actions',
      title: '',
      width: 'w-24',
      render: (_value, record) => {
        const isDeleting = deletingId === record.id;
        return (
          <div className="flex gap-1">
            <CustomButton
              type="text"
              size="icon-xs"
              onClick={() => onEdit(record)}
              disabled={isDeleting}
              aria-label="edit"
              className="text-muted-foreground hover:text-foreground"
            >
              <Pencil className="size-4" />
            </CustomButton>
            {isDeleting ? (
              <CustomButton type="text" size="icon-xs" disabled>
                <Loader2 className="size-4 animate-spin text-destructive" />
              </CustomButton>
            ) : (
              <CustomButton
                type="text"
                size="icon-xs"
                onClick={() => handleDelete(record.id)}
                aria-label="delete"
                className="text-destructive hover:text-destructive/90"
              >
                <Trash2 className="size-4" />
              </CustomButton>
            )}
          </div>
        );
      },
    },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="size-9 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return <CustomTable columns={columns} dataSource={rows} rowKey="id" />;
}
