'use client';

import {
  deleteChannelAtom,
  loadableChannelsAtom,
  upsertChannelAtom,
} from '@/atoms/IntegrationAtom';
import { CustomButton } from '@/components/shared';
import type { IntegrationRow } from '@/types/integration';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { useAtom } from 'jotai';
import { Loader2, Plus } from 'lucide-react';
import { useEffect, useState } from 'react';

import AddChannelModal from './AddChannelModal';
import IntegrationsTable from './IntegrationsTable';

export default function Integrations() {
  const [mounted, setMounted] = useState(false);
  const [channelsLoadable] = useAtom(loadableChannelsAtom);
  const [, upsertChannel] = useAtom(upsertChannelAtom);
  const [, removeChannel] = useAtom(deleteChannelAtom);
  const [modalOpen, setModalOpen] = useState(false);
  const [editRow, setEditRow] = useState<IntegrationRow | null>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleAdd = () => {
    setEditRow(null);
    setModalOpen(true);
  };

  const handleEdit = (row: IntegrationRow) => {
    setEditRow(row);
    setModalOpen(true);
  };

  const handleCloseModal = () => {
    setModalOpen(false);
    setEditRow(null);
  };

  const handleSubmit = async (data: {
    id?: number;
    name: string;
    type: string;
    auth_token: string;
    account_sid: string;
  }) => {
    const payload = {
      ...(data.id ? { id: data.id } : {}),
      name: data.name,
      type: data.type,
      meta_data: {
        account_sid: data.account_sid,
        auth_token: data.auth_token,
      },
    };

    try {
      await upsertChannel(payload as any);
      showToast.success(
        data.id ? 'Integration updated successfully' : 'Integration created successfully',
      );
    } catch (err) {
      handleApiError(err);
      throw new Error('API call failed');
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await removeChannel(id);
      showToast.success('Integration deleted successfully');
    } catch (error) {
      handleApiError(error);
    }
  };

  if (!mounted) {
    return (
      <div className="flex h-full w-full items-center justify-center p-4">
        <Loader2 className="size-10 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const isTableLoading = channelsLoadable.state === 'loading';
  const rows = channelsLoadable.state === 'hasData' ? channelsLoadable.data : [];

  return (
    <div className="w-full">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Integrations</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage your API keys and service connections
          </p>
        </div>
        <CustomButton type="primary" icon={<Plus size={18} />} onClick={handleAdd}>
          Add API key
        </CustomButton>
      </div>
      <IntegrationsTable
        rows={rows}
        loading={isTableLoading}
        onEdit={handleEdit}
        onDelete={handleDelete}
      />
      <AddChannelModal
        open={modalOpen}
        onClose={handleCloseModal}
        onSubmit={handleSubmit}
        editData={editRow}
      />
    </div>
  );
}
