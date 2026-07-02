'use client';

import React, { useEffect, useState } from 'react';
import { useSetAtom } from 'jotai';

import CustomModal from '@/components/shared/CustomModal';
import TextInput from '@/components/shared/TextInput';
import { cloneWorkflowAtom } from '@/atoms/WorkflowAtom';
import { showToast } from '@/utils/toast';
import { handleApiError } from '@/utils/helpers';
import type { WorkflowSummary } from '@/types/workflow';

interface Props {
  /** The workflow to duplicate — modal is open while non-null. */
  workflow: WorkflowSummary | null;
  onClose: () => void;
  /** Refresh the list; awaited so the modal loader stays up until it resolves. */
  onCloned: () => Promise<void> | void;
  /** Owning agent for the clone (defaults to the source workflow's owner). */
  agentId?: string;
}

const CloneWorkflowModal: React.FC<Props> = ({ workflow, onClose, onCloned, agentId }) => {
  const clone = useSetAtom(cloneWorkflowAtom);
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);

  // Pre-fill "<name> (clone)" each time a new workflow is targeted.
  useEffect(() => {
    if (workflow) setName(`${workflow.name} (clone)`);
  }, [workflow]);

  const submit = async () => {
    if (!workflow || loading) return;
    const trimmed = name.trim();
    if (!trimmed) {
      showToast.error('Name required');
      return;
    }
    setLoading(true);
    try {
      const created = await clone({ workflowId: workflow.id, name: trimmed, agentId });
      // Keep the modal + loader up until the refreshed list has loaded.
      await onCloned();
      showToast.success(`Cloned as “${created.name}”`);
      onClose();
    } catch (err) {
      handleApiError(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <CustomModal
      open={Boolean(workflow)}
      onClose={() => {
        if (!loading) onClose();
      }}
      title="Duplicate workflow"
      description={
        workflow
          ? `Creates a new draft copy of “${workflow.name}”. Agent assignments are not copied.`
          : undefined
      }
      confirmText="Duplicate"
      confirmLoading={loading}
      onConfirm={submit}
    >
      <div className="py-1">
        <TextInput
          name="clone-workflow-name"
          label="New workflow name"
          autoFocus
          placeholder="e.g. Inbound triage (clone)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submit()}
        />
      </div>
    </CustomModal>
  );
};

export default CloneWorkflowModal;
