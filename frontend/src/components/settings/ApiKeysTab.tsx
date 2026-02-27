'use client';

import { CustomButton, CustomModal, TextInput } from '@/components/shared';
import CustomTable from '@/components/shared/CustomTable';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { CustomTableColumn } from '@/types/components';
import { generateUUID } from '@/utils/helpers';
import { Eye, Key, MoreVertical, Plus, Trash2 } from 'lucide-react';
import { useState } from 'react';

export interface ApiKeyRow {
  id: string;
  name: string;
  keyValue: string;
  masked: boolean;
  createdAt: string;
  tag?: string;
}

export default function ApiKeysTab() {
  const [apiKeys, setApiKeys] = useState<ApiKeyRow[]>([]);
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [keyName, setKeyName] = useState('');

  const handleCreate = () => {
    if (keyName.trim()) {
      setApiKeys((prev) => [
        ...prev,
        {
          id: generateUUID(),
          name: keyName.trim(),
          keyValue: '•••••••••••',
          masked: true,
          createdAt: new Date().toLocaleString(undefined, {
            dateStyle: 'short',
            timeStyle: 'short',
          }),
        },
      ]);
      setKeyName('');
      setAddModalOpen(false);
    }
  };

  const handleCloseModal = () => {
    setKeyName('');
    setAddModalOpen(false);
  };

  const columns: CustomTableColumn<ApiKeyRow>[] = [
    {
      key: 'name',
      title: 'Name',
      dataIndex: 'name',
      render: (_value, record) => (
        <div className="flex items-center gap-2">
          <Key className="size-4 text-muted-foreground" />
          <span className="text-sm">{record.name}</span>
          {record.tag && (
            <Badge variant="outline" className="text-xs">
              {record.tag}
            </Badge>
          )}
        </div>
      ),
    },
    {
      key: 'keyValue',
      title: 'Key Value',
      dataIndex: 'keyValue',
    },
    {
      key: 'createdAt',
      title: 'Created at',
      dataIndex: 'createdAt',
    },
    {
      key: 'actions',
      title: '',
      width: 'w-14',
      render: (_value, _record) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <CustomButton
              type="text"
              size="icon-xs"
              className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <MoreVertical className="size-4" />
            </CustomButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem>
              <Eye className="size-4" />
              Reveal key
            </DropdownMenuItem>
            <DropdownMenuItem variant="destructive">
              <Trash2 className="size-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  return (
    <div>
      <div className="mb-4 flex justify-end">
        <CustomButton
          type="primary"
          icon={<Plus size={18} />}
          onClick={() => setAddModalOpen(true)}
        >
          Add API Key
        </CustomButton>
      </div>

      <CustomTable columns={columns} dataSource={apiKeys} rowKey="id" />

      <CustomModal
        open={addModalOpen}
        onClose={handleCloseModal}
        title="Add an API Key"
        confirmText="Create"
        onConfirm={handleCreate}
        confirmDisabled={!keyName.trim()}
      >
        <div>
          <TextInput
            name="api-key-name"
            label="Name this key"
            placeholder="e.g. Development"
            value={keyName}
            onChange={(e) => setKeyName(e.target.value)}
          />
        </div>
      </CustomModal>
    </div>
  );
}
