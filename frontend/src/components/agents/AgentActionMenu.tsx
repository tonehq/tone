'use client';

import { CustomButton, CustomModal } from '@/components/shared';
import { Pencil, Trash2 } from 'lucide-react';
import { useState } from 'react';

interface AgentActionMenuProps {
  onEdit: () => void;
  onDelete: () => Promise<void>;
}

export function AgentActionMenu({ onEdit, onDelete }: AgentActionMenuProps) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await onDelete();
    } finally {
      setDeleting(false);
      setConfirmOpen(false);
    }
  };

  return (
    <div className="flex items-center gap-1">
      <CustomButton
        type="text"
        size="icon-xs"
        onClick={(e) => {
          e.stopPropagation();
          onEdit();
        }}
        className="text-muted-foreground hover:text-foreground"
      >
        <Pencil className="size-4" />
        <span className="sr-only">Edit</span>
      </CustomButton>
      <CustomButton
        type="text"
        size="icon-xs"
        onClick={(e) => {
          e.stopPropagation();
          setConfirmOpen(true);
        }}
        aria-label="delete"
        className="text-destructive hover:text-destructive/90"
      >
        <Trash2 className="size-4" />
      </CustomButton>

      <CustomModal
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        title="Delete Agent"
        description="Are you sure you want to delete this agent? This action cannot be undone."
        confirmText="Delete"
        confirmType="danger"
        confirmLoading={deleting}
        onConfirm={handleDelete}
      />
    </div>
  );
}
