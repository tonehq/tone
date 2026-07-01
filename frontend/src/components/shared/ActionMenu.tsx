'use client';

import { CustomButton, CustomModal } from '@/components/shared';
import { Copy, Pencil, Trash2 } from 'lucide-react';
import { useState } from 'react';

export interface ActionMenuProps {
  onEdit: () => void;
  onDelete: () => Promise<void>;
  /** Optional duplicate action — renders a copy button between edit and delete when provided. */
  onClone?: () => void | Promise<void>;
  itemName?: string;
  deleteTitle?: string;
  deleteDescription?: string;
  confirmText?: string;
  editLabel?: string;
  deleteLabel?: string;
  cloneLabel?: string;
}

export default function ActionMenu({
  onEdit,
  onDelete,
  onClone,
  itemName,
  deleteTitle,
  deleteDescription,
  confirmText = 'Delete',
  editLabel = 'Edit',
  deleteLabel = 'Delete',
  cloneLabel = 'Duplicate',
}: ActionMenuProps) {
  const resolvedTitle = deleteTitle ?? (itemName ? `Delete ${itemName}?` : 'Delete');
  const resolvedDescription =
    deleteDescription ??
    (itemName
      ? `Are you sure you want to delete "${itemName}"? This action cannot be undone.`
      : 'Are you sure you want to delete this? This action cannot be undone.');
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
      {onClone && (
        <CustomButton
          type="text"
          size="icon-xs"
          onClick={(e) => {
            e.stopPropagation();
            void onClone();
          }}
          className="text-muted-foreground hover:text-foreground"
          aria-label={cloneLabel}
        >
          <Copy className="size-4" />
          <span className="sr-only">{cloneLabel}</span>
        </CustomButton>
      )}
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
        onClose={() => {
          if (!deleting) setConfirmOpen(false);
        }}
        title={resolvedTitle}
        description={resolvedDescription}
        confirmText={confirmText}
        confirmType="danger"
        confirmLoading={deleting}
        onConfirm={handleDelete}
      />
    </div>
  );
}
