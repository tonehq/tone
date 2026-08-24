'use client';

import CustomButton from '@/components/shared/CustomButton';
import {
  useCreateSipTrunk,
  useDeleteSipTrunk,
  useProvisionSipTrunk,
  useSipCarriers,
  useSipTrunks,
  useUpdateSipTrunk,
} from '@/lib/api/sipTrunks';
import type { SipTrunk, SipTrunkPayload } from '@/types/sipTrunk';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { AnimatePresence, motion } from 'framer-motion';
import { Plus } from 'lucide-react';
import { useCallback, useImperativeHandle, useState } from 'react';

import ChannelGridSkeleton from './channel-grid-skeleton';
import SipTrunkCard, { sipCardVariants } from './sip-trunk-card';
import SipTrunkFormModal from './sip-trunk-form-modal';

export interface SipTrunkGridHandle {
  openAdd: () => void;
}

interface SipTrunkGridProps {
  emptyMessage?: string;
  controlRef?: React.RefObject<SipTrunkGridHandle | null>;
}

export default function SipTrunkGrid({
  emptyMessage = 'No SIP trunks yet — bring your own carrier trunk to start.',
  controlRef,
}: SipTrunkGridProps) {
  const { data: trunks, isLoading, isFetched } = useSipTrunks();
  const { data: carriers } = useSipCarriers();
  const createTrunk = useCreateSipTrunk();
  const updateTrunk = useUpdateSipTrunk();
  const deleteTrunk = useDeleteSipTrunk();
  const provisionTrunk = useProvisionSipTrunk();

  const [modalOpen, setModalOpen] = useState(false);
  const [editTrunk, setEditTrunk] = useState<SipTrunk | null>(null);
  const [provisioningId, setProvisioningId] = useState<string | null>(null);

  const openAdd = useCallback(() => {
    setEditTrunk(null);
    setModalOpen(true);
  }, []);

  useImperativeHandle(controlRef, () => ({ openAdd }), [openAdd]);

  const handleEdit = useCallback((trunk: SipTrunk) => {
    setEditTrunk(trunk);
    setModalOpen(true);
  }, []);

  const handleDelete = useCallback(
    async (trunk: SipTrunk) => {
      try {
        await deleteTrunk.mutateAsync(trunk.id);
        showToast.success('SIP trunk deleted successfully');
      } catch (err) {
        handleApiError(err);
      }
    },
    [deleteTrunk],
  );

  const handleProvision = useCallback(
    async (trunk: SipTrunk) => {
      setProvisioningId(trunk.id);
      try {
        await provisionTrunk.mutateAsync(trunk.id);
        showToast.success(`${trunk.name} provisioned with ${trunk.carrier}`);
      } catch (err) {
        handleApiError(err);
      } finally {
        setProvisioningId(null);
      }
    },
    [provisionTrunk],
  );

  const handleSubmit = useCallback(
    async (payload: SipTrunkPayload, trunkId?: string) => {
      try {
        if (trunkId) {
          await updateTrunk.mutateAsync({ trunkId, payload });
          showToast.success('SIP trunk updated successfully');
          return;
        }
        await createTrunk.mutateAsync(payload);
        showToast.success('SIP trunk created — provision it to push the config live');
      } catch (err) {
        handleApiError(err);
        throw err;
      }
    },
    [createTrunk, updateTrunk],
  );

  const closeModal = () => {
    setModalOpen(false);
    setEditTrunk(null);
  };

  const addRow = (
    <CustomButton
      type="text"
      fullWidth
      onClick={openAdd}
      className={cn(
        '!h-auto group flex cursor-pointer items-center justify-center gap-2 rounded-2xl border border-dashed border-foreground/15 bg-transparent px-4 py-3 text-xs font-medium text-muted-foreground transition-all',
        'hover:border-foreground/30 hover:bg-background hover:text-foreground hover:shadow-sm',
      )}
    >
      <Plus className="size-3.5 transition-transform group-hover:scale-110" />
      Add SIP trunk
    </CustomButton>
  );

  const body = (() => {
    if (isLoading) {
      return <ChannelGridSkeleton />;
    }
    if (isFetched && (trunks?.length ?? 0) === 0) {
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
          {(trunks ?? []).map((trunk) => (
            <motion.div
              key={trunk.id}
              layout
              variants={sipCardVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
            >
              <SipTrunkCard
                trunk={trunk}
                provisioning={provisioningId === trunk.id}
                onEdit={handleEdit}
                onDelete={handleDelete}
                onProvision={handleProvision}
              />
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
      <SipTrunkFormModal
        open={modalOpen}
        onClose={closeModal}
        onSubmit={handleSubmit}
        editTrunk={editTrunk}
        carriers={carriers ?? ['telnyx', 'generic']}
      />
    </>
  );
}
