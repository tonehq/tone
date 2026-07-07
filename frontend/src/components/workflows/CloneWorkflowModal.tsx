'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { useSetAtom } from 'jotai';

import CustomModal from '@/components/shared/CustomModal';
import SearchableSelect from '@/components/shared/SearchableSelect';
import TextInput from '@/components/shared/TextInput';
import { cloneWorkflowAtom } from '@/atoms/WorkflowAtom';
import { getAllAgents } from '@/services/agentsService';
import type { AgentDropdownItem } from '@/types/agent';
import type { WorkflowSummary } from '@/types/workflow';
import { showToast } from '@/utils/toast';
import { handleApiError } from '@/utils/helpers';

interface Props {
  workflow: WorkflowSummary | null;
  onClose: () => void;
  onCloned: () => Promise<void> | void;
  agentId?: string;
}

const CloneWorkflowModal: React.FC<Props> = ({ workflow, onClose, onCloned, agentId }) => {
  const clone = useSetAtom(cloneWorkflowAtom);
  const [name, setName] = useState('');
  const [targetAgentId, setTargetAgentId] = useState('');
  const [agents, setAgents] = useState<AgentDropdownItem[]>([]);
  const [agentsLoading, setAgentsLoading] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (workflow) {
      setName(`${workflow.name} (clone)`);
      setTargetAgentId(agentId ?? '');
    }
  }, [workflow, agentId]);

  useEffect(() => {
    if (!workflow) return;
    let cancelled = false;
    setAgentsLoading(true);
    getAllAgents()
      .then((rows) => {
        if (!cancelled) setAgents(rows);
      })
      .catch((err) => {
        if (!cancelled) handleApiError(err);
      })
      .finally(() => {
        if (!cancelled) setAgentsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [workflow]);

  const agentOptions = useMemo(() => agents.map((a) => ({ value: a.id, label: a.name })), [agents]);

  const submit = async () => {
    if (!workflow || loading) return;
    const trimmed = name.trim();
    if (!trimmed) {
      showToast.error('Name required');
      return;
    }
    if (!targetAgentId) {
      showToast.error('Select a target agent');
      return;
    }
    setLoading(true);
    try {
      const created = await clone({
        workflowId: workflow.id,
        name: trimmed,
        agentId: targetAgentId,
      });
      await onCloned();
      const targetName = agents.find((a) => a.id === targetAgentId)?.name;
      showToast.success(
        'Workflow cloned',
        targetName
          ? `“${workflow.name}” cloned as “${created.name}” to ${targetName}`
          : `“${workflow.name}” cloned as “${created.name}”`,
      );
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
          ? `Creates a new draft copy of “${workflow.name}” in the selected agent. Agent version assignments are not copied.`
          : undefined
      }
      confirmText="Duplicate"
      confirmLoading={loading}
      onConfirm={submit}
    >
      <div className="flex flex-col gap-4 py-1">
        <TextInput
          name="clone-workflow-name"
          label="New workflow name"
          autoFocus
          placeholder="e.g. Inbound triage (clone)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submit()}
        />
        <SearchableSelect
          name="clone-workflow-agent"
          label="Copy to agent"
          isRequired
          options={agentOptions}
          value={targetAgentId}
          onValueChange={setTargetAgentId}
          loading={agentsLoading}
          placeholder="Select an agent"
          searchPlaceholder="Search agents…"
          emptyMessage="No agents found."
        />
      </div>
    </CustomModal>
  );
};

export default CloneWorkflowModal;
