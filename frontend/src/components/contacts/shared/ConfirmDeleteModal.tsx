'use client';

import { CustomModal } from '@/components/shared';

/**
 * A thin, destructive-action wrapper over `CustomModal` for the contacts feature.
 *
 * WHAT: renders a confirm dialog with a red confirm button, an optional impact-summary
 * body (e.g. "3 contacts, 2 scheduled calls will be permanently deleted"), and a
 * loading state on confirm. Radix (via CustomModal) provides focus trap + ARIA.
 *
 * WHEN: use for every destructive confirm in the feature — directory delete (with the
 * `DirectoryDeleteImpact` counts), contact delete/bulk-delete, schema delete, and
 * unassign. Callers pass their own summary node; this component owns the dialog chrome.
 */
export interface ConfirmDeleteModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  /** Dialog title, e.g. "Delete directory". */
  title: string;
  /** Optional short prompt under the title, e.g. "This cannot be undone." */
  description?: string;
  /**
   * Optional impact summary rendered in the body — a list of what will be deleted /
   * detached. Pass the `DirectoryDeleteImpact` breakdown here for a directory delete.
   */
  impact?: React.ReactNode;
  confirmText?: string;
  cancelText?: string;
  /** Show a spinner + disable buttons while the delete request is in flight. */
  loading?: boolean;
  /** Disable confirm (e.g. while the impact counts are still loading). */
  confirmDisabled?: boolean;
}

export default function ConfirmDeleteModal({
  open,
  onClose,
  onConfirm,
  title,
  description,
  impact,
  confirmText = 'Delete',
  cancelText = 'Cancel',
  loading = false,
  confirmDisabled = false,
}: ConfirmDeleteModalProps) {
  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title={title}
      description={description}
      confirmText={confirmText}
      cancelText={cancelText}
      confirmType="danger"
      confirmLoading={loading}
      confirmDisabled={confirmDisabled}
      onConfirm={onConfirm}
      width="sm:max-w-md"
    >
      {impact != null && <div className="text-sm text-muted-foreground">{impact}</div>}
    </CustomModal>
  );
}
