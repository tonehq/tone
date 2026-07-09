'use client';

import { ActionMenu } from '@/components/shared';

interface AgentActionMenuProps {
  agentName?: string;
  onEdit: () => void;
  onDelete: () => Promise<void>;
  /** When provided, renders a Clone (copy) button between Edit and Delete. */
  onClone?: () => void | Promise<void>;
}

export function AgentActionMenu({ agentName, onEdit, onDelete, onClone }: AgentActionMenuProps) {
  return (
    <ActionMenu
      onEdit={onEdit}
      onDelete={onDelete}
      onClone={onClone}
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
      cloneLabel="Clone"
    />
  );
}
