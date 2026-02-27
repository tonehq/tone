'use client';

import { CustomButton, CustomModal } from '@/components/shared';
import { Pencil, Trash2 } from 'lucide-react';
import { useState } from 'react';

export interface ActionMenuProps {
  onEdit: () => void;
  onDelete: () => Promise<void>;
  deleteTitle?: string;
  deleteDescription?: string;
  confirmText?: string;
  editLabel?: string;
  deleteLabel?: string;
}

export default function ActionMenu({
  onEdit,
  onDelete,
  deleteTitle = 'Delete',
  deleteDescription = 'Are you sure you want to delete this? This action cannot be undone.',
  confirmText = 'Delete',
  editLabel = 'Edit',
  deleteLabel = 'Delete',
}: ActionMenuProps) {
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
        aria-label={editLabel}
      >
        <Pencil className="size-4" />
        <span className="sr-only">{editLabel}</span>
      </CustomButton>
      <CustomButton
        type="text"
        size="icon-xs"
        onClick={(e) => {
          e.stopPropagation();
          setConfirmOpen(true);
        }}
        aria-label={deleteLabel}
        className="text-destructive hover:text-destructive/90"
      >
        <Trash2 className="size-4" />
        <span className="sr-only">{deleteLabel}</span>
      </CustomButton>

      <CustomModal
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        title={deleteTitle}
        description={deleteDescription}
        confirmText={confirmText}
        confirmType="danger"
        confirmLoading={deleting}
        onConfirm={handleDelete}
      />
    </div>
  );
}
