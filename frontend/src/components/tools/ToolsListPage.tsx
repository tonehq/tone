'use client';

import { deleteToolAtom, fetchToolsAtom, toolsAtom } from '@/atoms/ToolAtom';
import { ActionMenu, CustomButton, CustomTable, TextInput } from '@/components/shared';
import type { CustomTableColumn } from '@/types/components';
import type { Tool } from '@/types/tool';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { useAtom } from 'jotai';
import { Plus, Search, Wrench } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';

const METHOD_COLORS: Record<string, string> = {
  GET: 'bg-emerald-500/15 text-emerald-600',
  POST: 'bg-blue-500/15 text-blue-600',
  PUT: 'bg-amber-500/15 text-amber-600',
  DELETE: 'bg-red-500/15 text-red-600',
  PATCH: 'bg-violet-500/15 text-violet-600',
};

export default function ToolsListPage() {
  const router = useRouter();
  const [{ tools, loading }] = useAtom(toolsAtom);
  const [, fetchTools] = useAtom(fetchToolsAtom);
  const [, deleteToolAction] = useAtom(deleteToolAtom);

  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchTools().catch(handleApiError);
  }, [fetchTools]);

  const filteredTools = useMemo(() => {
    if (!search.trim()) return tools;
    const q = search.toLowerCase();
    return tools.filter(
      (t) =>
        t.name.toLowerCase().includes(q) ||
        t.description.toLowerCase().includes(q) ||
        t.url.toLowerCase().includes(q),
    );
  }, [tools, search]);

  const handleEdit = useCallback(
    (tool: Tool) => {
      router.push(`/tools/edit/${tool.id}`);
    },
    [router],
  );

  const handleDelete = useCallback(
    async (tool: Tool) => {
      try {
        await deleteToolAction(tool.id);
        showToast.success('Tool deleted successfully');
        await fetchTools();
      } catch (error) {
        handleApiError(error);
      }
    },
    [deleteToolAction, fetchTools],
  );

  const columns: CustomTableColumn<Tool>[] = useMemo(
    () => [
      {
        key: 'name',
        dataIndex: 'name',
        title: 'Name',
        width: '220px',
        render: (_val: unknown, record: Tool) => (
          <div className="min-w-0">
            <p className="truncate font-mono text-[13px] font-medium text-foreground">
              {record.name}
            </p>
            <p className="mt-0.5 truncate text-[12px] text-muted-foreground">
              {record.description}
            </p>
          </div>
        ),
      },
      {
        key: 'method',
        dataIndex: 'method',
        title: 'Method',
        width: '90px',
        render: (_val: unknown, record: Tool) => {
          const m = record.method?.toUpperCase() ?? 'POST';
          return (
            <span
              className={cn(
                'inline-flex rounded-md px-2 py-0.5 text-[11px] font-semibold',
                METHOD_COLORS[m] ?? 'bg-muted text-muted-foreground',
              )}
            >
              {m}
            </span>
          );
        },
      },
      {
        key: 'url',
        dataIndex: 'url',
        title: 'Endpoint URL',
        render: (_val: unknown, record: Tool) => (
          <span className="truncate font-mono text-[12px] text-muted-foreground">{record.url}</span>
        ),
      },
      {
        key: 'auth_type',
        dataIndex: 'auth_type',
        title: 'Auth',
        width: '100px',
        render: (_val: unknown, record: Tool) => (
          <span className="text-[12px] capitalize text-muted-foreground">
            {!record.auth_type || record.auth_type === 'none'
              ? '-'
              : record.auth_type.replace('_', ' ')}
          </span>
        ),
      },
      {
        key: 'params',
        title: 'Params',
        width: '80px',
        render: (_val: unknown, record: Tool) => {
          const count = Object.keys(record.parameters?.properties ?? {}).length;
          return (
            <span className="text-[12px] text-muted-foreground">
              {count > 0 ? `${count} param${count > 1 ? 's' : ''}` : '-'}
            </span>
          );
        },
      },
      {
        key: 'status',
        dataIndex: 'is_active',
        title: 'Status',
        width: '80px',
        render: (_val: unknown, record: Tool) => (
          <span
            className={cn(
              'inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium',
              record.is_active
                ? 'bg-emerald-500/15 text-emerald-600'
                : 'bg-muted text-muted-foreground',
            )}
          >
            {record.is_active ? 'Active' : 'Inactive'}
          </span>
        ),
      },
      {
        key: 'actions',
        title: '',
        width: '80px',
        align: 'right' as const,
        render: (_val: unknown, record: Tool) => (
          <ActionMenu
            onEdit={() => handleEdit(record)}
            onDelete={() => handleDelete(record)}
            itemName={record.name}
          />
        ),
      },
    ],
    [handleEdit, handleDelete],
  );

  const emptyState = (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="flex size-14 items-center justify-center rounded-2xl bg-muted/50">
        <Wrench size={24} className="text-muted-foreground" />
      </div>
      <p className="mt-4 text-[14px] font-medium text-foreground">
        {search ? 'No tools match your search' : 'No tools yet'}
      </p>
      <p className="mt-1.5 max-w-[300px] text-[13px] leading-relaxed text-muted-foreground">
        {search
          ? 'Try a different search term.'
          : 'Create your first tool to give your agents the ability to call external APIs.'}
      </p>
      {!search && (
        <CustomButton
          type="primary"
          icon={<Plus size={14} />}
          className="mt-5"
          onClick={() => router.push('/tools/create')}
        >
          Create Tool
        </CustomButton>
      )}
    </div>
  );

  return (
    <div className="flex h-full flex-col gap-5 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-foreground">Tools</h1>
          <p className="mt-1 text-[13px] text-muted-foreground">
            Define external API tools your voice agents can call during conversations.
          </p>
        </div>
        <CustomButton
          type="primary"
          icon={<Plus size={14} />}
          onClick={() => router.push('/tools/create')}
        >
          Create Tool
        </CustomButton>
      </div>

      {/* Search */}
      {tools.length > 0 && (
        <div className="max-w-sm">
          <TextInput
            name="tool-search"
            placeholder="Search tools..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            leftIcon={<Search size={16} />}
          />
        </div>
      )}

      {/* Table */}
      <CustomTable<Tool>
        columns={columns}
        dataSource={filteredTools}
        rowKey="id"
        loading={loading}
        emptyState={emptyState}
        pagination={{ pageSize: 20 }}
        onRowClick={handleEdit}
      />
    </div>
  );
}
