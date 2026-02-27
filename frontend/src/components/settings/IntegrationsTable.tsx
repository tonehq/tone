'use client';

import CustomTable from '@/components/shared/CustomTable';
import { Button } from '@/components/ui/button';
import type { CustomTableColumn } from '@/types/components';
import type { IntegrationRow } from '@/types/integration';
import { Check, Copy, Eye, EyeOff, Loader2, Pencil, Trash2 } from 'lucide-react';
import { useState } from 'react';

interface IntegrationsTableProps {
  rows: IntegrationRow[];
  loading?: boolean;
  onEdit: (row: IntegrationRow) => void;
  onDelete: (id: number) => Promise<void>;
}

function AuthTokenCell({ token }: { token: string }) {
  const [visible, setVisible] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(token);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex items-center gap-1.5">
      <span className="font-mono text-sm">
        {visible ? token : '••••••••••••'}
      </span>
      <Button
        variant="ghost"
        size="icon-xs"
        onClick={() => setVisible((v) => !v)}
        aria-label={visible ? 'hide token' : 'show token'}
      >
        {visible ? (
          <EyeOff className="size-3.5 text-muted-foreground" />
        ) : (
          <Eye className="size-3.5 text-muted-foreground" />
        )}
      </Button>
      <Button
        variant="ghost"
        size="icon-xs"
        onClick={handleCopy}
        aria-label="copy token"
      >
        {copied ? (
          <Check className="size-3.5 text-emerald-500" />
        ) : (
          <Copy className="size-3.5 text-muted-foreground" />
        )}
      </Button>
    </div>
  );
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
    {
      key: 'auth_token',
      title: 'Auth Token',
      render: (_value, record) => <AuthTokenCell token={record.auth_token} />,
    },
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
