'use client';

import React, { useEffect, useState } from 'react';
import { useSetAtom } from 'jotai';

import CustomModal from '@/components/shared/CustomModal';
import TextInput from '@/components/shared/TextInput';
import { saveAgentAsTemplateAtom } from '@/atoms/AgentsAtom';
import { showToast } from '@/utils/toast';
import { handleApiError } from '@/utils/helpers';

/** Minimal shape needed to seed and label the save-as-template dialog. */
interface SaveAsTemplateTarget {
  id: string;
  name: string;
}

interface Props {
  agent: SaveAsTemplateTarget | null;
  onClose: () => void;
}

// Matches the `agent_configs.name` column limit (String(200)) enforced server-side.
const MAX_NAME_LEN = 200;

const SaveAsTemplateModal: React.FC<Props> = ({ agent, onClose }) => {
  const saveAsTemplate = useSetAtom(saveAgentAsTemplateAtom);
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);

  // Pre-fill with the agent name so the user has a sensible starting label; a
  // template name is required (unlike clone, there is no server-side default).
  const defaultName = agent ? agent.name.slice(0, MAX_NAME_LEN) : '';

  useEffect(() => {
    if (agent) setName(defaultName);
  }, [agent, defaultName]);

  const submit = async () => {
    if (!agent || loading) return;
    const trimmed = name.trim();
    if (!trimmed) {
      showToast.error('Template name required');
      return;
    }
    setLoading(true);
    try {
      await saveAsTemplate({ agentId: agent.id, name: trimmed });
      showToast.success('Template saved', `“${trimmed}” is now available as a template`);
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
      title="Save as template"
      description={
        agent
          ? `Saves the current live configuration of “${agent.name}” — including its tools, MCP servers, knowledge bases and workflow — as a reusable template. Others can start a new agent from it.`
          : undefined
      }
      confirmText="Save template"
      confirmLoading={loading}
      confirmDisabled={!name.trim()}
      onConfirm={submit}
    >
      <div className="flex flex-col gap-4 py-1">
        <TextInput
          name="template-name"
          label="Template name"
          autoFocus
          maxLength={MAX_NAME_LEN}
          placeholder="e.g. Hospital front-desk template"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submit()}
        />
      </div>
    </CustomModal>
  );
};

export default SaveAsTemplateModal;
