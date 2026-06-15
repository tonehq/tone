'use client';

import React, { useState } from 'react';
import { useSetAtom } from 'jotai';
import { useRouter } from 'next/navigation';

import CustomModal from '@/components/shared/CustomModal';
import { createWorkflowAtom } from '@/atoms/WorkflowAtom';
import { showToast } from '@/utils/toast';
import { handleApiError } from '@/utils/helpers';

interface Props {
  open: boolean;
  onClose: () => void;
}

const inputCls =
  'w-full rounded-md border border-border bg-background px-2.5 py-1.5 text-sm outline-none ring-primary/40 placeholder:text-muted-foreground focus:ring-2';

const CreateWorkflowModal: React.FC<Props> = ({ open, onClose }) => {
  const router = useRouter();
  const create = useSetAtom(createWorkflowAtom);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);

  const reset = () => {
    setName('');
    setDescription('');
  };

  const submit = async () => {
    if (!name.trim()) {
      showToast.error('Name required');
      return;
    }
    setLoading(true);
    try {
      const wf = await create({ name: name.trim(), description: description.trim() || undefined });
      reset();
      onClose();
      router.push(`/workflows/${wf.id}`);
    } catch (err) {
      handleApiError(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <CustomModal
      open={open}
      onClose={() => {
        reset();
        onClose();
      }}
      title="New workflow"
      confirmText="Create & open"
      confirmLoading={loading}
      onConfirm={submit}
    >
      <div className="flex flex-col gap-4 py-1">
        <div>
          <label className="mb-1.5 block text-sm font-medium text-foreground">Name</label>
          <input
            autoFocus
            className={inputCls}
            placeholder="e.g. Inbound triage"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submit()}
          />
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-medium text-foreground">
            Description (optional)
          </label>
          <textarea
            className={`${inputCls} min-h-[70px] resize-y`}
            placeholder="What does this workflow do?"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
      </div>
    </CustomModal>
  );
};

export default CreateWorkflowModal;
