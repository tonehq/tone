'use client';

import { ActionMenu } from '@/components/shared';

interface AgentActionMenuProps {
  onEdit: () => void;
  onDelete: () => Promise<void>;
}

export function AgentActionMenu({ onEdit, onDelete }: AgentActionMenuProps) {
  return (
    <ActionMenu
      onEdit={onEdit}
      onDelete={onDelete}
      deleteTitle="Delete Agent"
      deleteDescription="Are you sure you want to delete this agent? This action cannot be undone."
      confirmText="Delete"
      editLabel="Edit"
      deleteLabel="Delete"
    />
  );
}
