'use client';

import { ActionMenu } from '@/components/shared';

interface AgentActionMenuProps {
  agentName?: string;
  onEdit: () => void;
  onDelete: () => Promise<void>;
}

export function AgentActionMenu({ agentName, onEdit, onDelete }: AgentActionMenuProps) {
  return (
    <ActionMenu
      onEdit={onEdit}
      onDelete={onDelete}
      itemName={agentName}
      deleteTitle={agentName ? `Delete ${agentName}?` : 'Delete Agent'}
      deleteDescription={
        agentName
          ? `Are you sure you want to delete "${agentName}"? This action cannot be undone.`
          : 'Are you sure you want to delete this agent? This action cannot be undone.'
      }
      confirmText="Delete"
      editLabel="Edit"
      deleteLabel="Delete"
    />
  );
}
