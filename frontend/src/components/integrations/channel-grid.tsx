'use client';

import {
  channelsAtom,
  deleteChannelAtom,
  fetchChannelsAtom,
  upsertChannelAtom,
} from '@/atoms/IntegrationAtom';
import type { Channel, ChannelUpsertPayload } from '@/types/integration';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { AnimatePresence, motion } from 'framer-motion';
import { useAtomValue, useSetAtom } from 'jotai';
import { Plus } from 'lucide-react';
import { useCallback, useEffect, useImperativeHandle, useState } from 'react';

import ChannelCard, { cardVariants } from './channel-card';
import ChannelFormModal from './channel-form-modal';
import ChannelGridSkeleton from './channel-grid-skeleton';

export interface ChannelGridHandle {
  openAdd: (providerKey?: string | null) => void;
}

interface ChannelGridProps {
  emptyMessage?: string;
  controlRef?: React.RefObject<ChannelGridHandle | null>;
}

export default function ChannelGrid({
  emptyMessage = 'No telephony channels yet — add your first one.',
  controlRef,
}: ChannelGridProps) {
  const state = useAtomValue(channelsAtom);
  const fetchList = useSetAtom(fetchChannelsAtom);
  const upsert = useSetAtom(upsertChannelAtom);
  const remove = useSetAtom(deleteChannelAtom);

  const [modalOpen, setModalOpen] = useState(false);
  const [editChannel, setEditChannel] = useState<Channel | null>(null);
  const [providerKey, setProviderKey] = useState<string | null>(null);

  useEffect(() => {
    if (!state.initialized && state.status !== 'loading') {
      fetchList().catch((err) => handleApiError(err));
    }
  }, [state.initialized, state.status, fetchList]);

  const openAdd = useCallback((key?: string | null) => {
    setEditChannel(null);
    setProviderKey(key ?? null);
    setModalOpen(true);
  }, []);

  useImperativeHandle(controlRef, () => ({ openAdd }), [openAdd]);

  const handleEdit = useCallback((channel: Channel) => {
    setEditChannel(channel);
    setProviderKey(channel.channel_type);
    setModalOpen(true);
  }, []);

  const handleDelete = useCallback(
    async (channel: Channel) => {
      try {
        await remove(channel.id);
        showToast.success('Integration deleted successfully');
      } catch (err) {
        handleApiError(err);
      }
    },
    [remove],
  );

  const handleSubmit = useCallback(
    async (payload: ChannelUpsertPayload) => {
      try {
        await upsert(payload);
        showToast.success(
          payload.id ? 'Integration updated successfully' : 'Integration created successfully',
        );
      } catch (err) {
        handleApiError(err);
        throw err;
      }
    },
    [upsert],
  );

  const closeModal = () => {
    setModalOpen(false);
    setEditChannel(null);
    setProviderKey(null);
  };

  const addRow = (
    <button
      type="button"
      onClick={() => openAdd(null)}
      className={cn(
        'group flex w-full cursor-pointer items-center justify-center gap-2 rounded-2xl border border-dashed border-foreground/15 bg-transparent px-4 py-3 text-xs font-medium text-muted-foreground transition-all',
        'hover:border-foreground/30 hover:bg-background hover:text-foreground hover:shadow-sm',
      )}
    >
      <Plus className="size-3.5 transition-transform group-hover:scale-110" />
      Add channel
    </button>
  );

  const body = (() => {
    if (!state.initialized && state.status === 'loading') {
      return <ChannelGridSkeleton />;
    }
    if (state.initialized && state.items.length === 0) {
      return (
        <div className="flex flex-col gap-2">
          <div className="rounded-xl border border-dashed border-border/70 bg-muted/20 px-4 py-6 text-center text-sm text-muted-foreground">
            {emptyMessage}
          </div>
          {addRow}
        </div>
      );
    }
    return (
      <div className="flex flex-col gap-2">
        <AnimatePresence initial={false}>
          {state.items.map((channel) => (
            <motion.div
              key={channel.id}
              layout
              variants={cardVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
            >
              <ChannelCard channel={channel} onEdit={handleEdit} onDelete={handleDelete} />
            </motion.div>
          ))}
        </AnimatePresence>

        {addRow}
      </div>
    );
  })();

  return (
    <>
      {body}
      <ChannelFormModal
        open={modalOpen}
        onClose={closeModal}
        onSubmit={handleSubmit}
        editChannel={editChannel}
        providerKey={providerKey}
      />
    </>
  );
}
