'use client';

import CustomTable from '@/components/shared/CustomTable';
import { Button } from '@/components/ui/button';
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
      title: 'Actions',
      width: 'w-24',
      render: (_value, record) => {
        const isDeleting = deletingId === record.id;
        return (
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="icon-xs"
              onClick={() => onEdit(record)}
              disabled={isDeleting}
              aria-label="edit"
            >
              <Pencil className="size-4 text-muted-foreground" />
            </Button>
            {isDeleting ? (
              <Button variant="ghost" size="icon-xs" disabled>
                <Loader2 className="size-4 animate-spin text-destructive" />
              </Button>
            ) : (
              <Button
                variant="ghost"
                size="icon-xs"
                onClick={() => handleDelete(record.id)}
                aria-label="delete"
              >
                <Trash2 className="size-4 text-destructive" />
              </Button>
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
