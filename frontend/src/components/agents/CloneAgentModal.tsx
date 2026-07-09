'use client';

import React, { useEffect, useState } from 'react';
import { useSetAtom } from 'jotai';

import CustomModal from '@/components/shared/CustomModal';
import TextInput from '@/components/shared/TextInput';
import { cloneAgentAtom } from '@/atoms/AgentsAtom';
import { showToast } from '@/utils/toast';
import { handleApiError } from '@/utils/helpers';

/** Minimal shape needed to seed and label the clone dialog. */
interface CloneAgentTarget {
  id: string;
  name: string;
}

interface Props {
  agent: CloneAgentTarget | null;
  onClose: () => void;
  onCloned: () => Promise<void> | void;
}

// Matches the `agents.name` column limit (String(50)) enforced server-side.
const MAX_NAME_LEN = 50;

const CloneAgentModal: React.FC<Props> = ({ agent, onClose, onCloned }) => {
  const clone = useSetAtom(cloneAgentAtom);
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);

  // The name we pre-filled. When left untouched we submit blank so the server
  // applies its own "(copy)" default and auto-numbers on collision, letting the
  // same agent be cloned repeatedly instead of 409-ing on the second attempt.
  const defaultName = agent ? `${agent.name} (copy)`.slice(0, MAX_NAME_LEN) : '';

  useEffect(() => {
    if (agent) setName(defaultName);
  }, [agent, defaultName]);

  const submit = async () => {
    if (!agent || loading) return;
    const trimmed = name.trim();
    if (!trimmed) {
      showToast.error('Name required');
      return;
    }
    setLoading(true);
    try {
      // Unedited default → send blank so the server auto-names / auto-numbers.
      const payloadName = trimmed === defaultName.trim() ? undefined : trimmed;
      const created = await clone({ agentId: agent.id, name: payloadName });
      await onCloned();
      showToast.success('Agent cloned', `Created “${created.name}”`);
      onClose();
    } catch (err) {
      handleApiError(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <CustomModal
      open={Boolean(agent)}
      onClose={() => {
        if (!loading) onClose();
      }}
      title="Clone agent"
      description={
        agent
          ? `Creates a full copy of “${agent.name}” — including its configuration, tools, MCP servers and knowledge bases. Phone numbers are not copied.`
          : undefined
      }
      confirmText="Clone"
      confirmLoading={loading}
      confirmDisabled={!name.trim()}
      onConfirm={submit}
    >
      <div className="flex flex-col gap-4 py-1">
        <TextInput
          name="clone-agent-name"
          label="New agent name"
          autoFocus
          maxLength={MAX_NAME_LEN}
          placeholder="e.g. Hospital agent (copy)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submit()}
        />
      </div>
    </CustomModal>
  );
};

export default CloneAgentModal;
