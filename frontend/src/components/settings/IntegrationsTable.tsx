'use client';

import { ActionMenu, CustomButton } from '@/components/shared';
import CustomTable from '@/components/shared/CustomTable';
import type { CustomTableColumn } from '@/types/components';
import type { IntegrationRow } from '@/types/integration';
import { Check, Copy, Eye, EyeOff, Loader2 } from 'lucide-react';
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
      <span
        className="inline-block w-[160px] overflow-hidden text-ellipsis whitespace-nowrap font-mono text-sm"
        title={token}
      >
        {visible ? token : '••••••••••••'}
      </span>
      <CustomButton
        type="text"
        size="icon-xs"
        htmlType="button"
        onClick={() => setVisible((v) => !v)}
        aria-label={visible ? 'hide token' : 'show token'}
        className="p-0"
      >
        {visible ? (
          <EyeOff className="size-3.5 text-muted-foreground" />
        ) : (
          <Eye className="size-3.5 text-muted-foreground" />
        )}
      </CustomButton>
      <CustomButton
        type="text"
        size="icon-xs"
        htmlType="button"
        onClick={handleCopy}
        aria-label="copy token"
        className="p-0"
      >
        {copied ? (
          <Check className="size-3.5 text-emerald-500" />
        ) : (
          <Copy className="size-3.5 text-muted-foreground" />
        )}
      </CustomButton>
    </div>
  );
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
    {
      key: 'auth_token',
      title: 'Auth Token',
      render: (_value, record) => <AuthTokenCell token={record.auth_token} />,
    },
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
