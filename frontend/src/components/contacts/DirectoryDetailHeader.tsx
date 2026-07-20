'use client';

import { ChevronRight, Pencil, Trash2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import ConfirmDeleteModal from '@/components/contacts/shared/ConfirmDeleteModal';
import DirectoryFormModal from '@/components/contacts/DirectoryFormModal';
import { CustomButton } from '@/components/shared';
import {
  useDeleteDirectory,
  useDirectory,
  useDirectoryDeleteImpact,
} from '@/lib/api/contactDirectories';
import { useAuthStore } from '@/stores/auth';
import type { DirectoryDeleteImpact } from '@/types/contactDirectory';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

/**
 * Right-pane header for a single directory.
 *
 * WHAT: shows the directory name, a `Directories › {name}` breadcrumb, and edit +
 * delete actions (admin/owner only). Delete opens `ConfirmDeleteModal` with the
 * `delete-impact` blast radius (permanent-deletion warning) before calling the
 * hard-delete endpoint, then navigates back to `/contacts/directories`. Datasource
 * schemas are now a section inside Contacts (`/contacts/datasource`), so this header no
 * longer carries a General/Schema tab — a directory detail shows only its contacts.
 *
 * WHEN: rendered by the directory-detail (General) route page.
 */
export interface DirectoryDetailHeaderProps {
  directoryId: string;
}

export default function DirectoryDetailHeader({ directoryId }: DirectoryDetailHeaderProps) {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const isAdminOrOwner = user?.role === 'admin' || user?.role === 'owner';

  const { data: directory } = useDirectory(directoryId);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const deleteDirectory = useDeleteDirectory();
  // Fetched lazily only while the confirm modal is open.
  const { data: impact, isLoading: impactLoading } = useDirectoryDeleteImpact(
    deleteOpen ? directoryId : null,
  );

  const name = directory?.name ?? '';

  const handleDelete = async () => {
    try {
      await deleteDirectory.mutateAsync(directoryId);
      showToast.success(
        'Directory deleted',
        name ? `"${name}" was permanently deleted.` : undefined,
      );
      setDeleteOpen(false);
      router.replace('/contacts/directories');
    } catch (error) {
      handleApiError(error);
    }
  };

  return (
    <div className="flex shrink-0 flex-col gap-3 border-b border-border px-6 py-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <nav
            aria-label="Breadcrumb"
            className="flex items-center gap-1 text-xs text-muted-foreground"
          >
            <span>Directories</span>
            <ChevronRight className="size-3.5" />
            <span className="truncate text-foreground/80">{name || '…'}</span>
          </nav>
          <h1 className="mt-1 truncate text-xl font-semibold text-foreground">{name || '…'}</h1>
        </div>

        {isAdminOrOwner && (
          <div className="flex shrink-0 items-center gap-2">
            <CustomButton
              type="default"
              size="sm"
              icon={<Pencil className="size-3.5" />}
              onClick={() => setEditOpen(true)}
            >
              Edit
            </CustomButton>
            <CustomButton
              type="danger"
              size="sm"
              icon={<Trash2 className="size-3.5" />}
              onClick={() => setDeleteOpen(true)}
            >
              Delete
            </CustomButton>
          </div>
        )}
      </div>

      <DirectoryFormModal
        open={editOpen}
        onClose={() => setEditOpen(false)}
        directory={directory ?? null}
      />

      <ConfirmDeleteModal
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        onConfirm={handleDelete}
        title="Delete directory"
        description="This directory and its data will be permanently deleted. This cannot be undone."
        confirmText="Permanently delete"
        loading={deleteDirectory.isPending}
        confirmDisabled={impactLoading}
        impact={<DeleteImpactSummary impact={impact} loading={impactLoading} />}
      />
    </div>
  );
}

function DeleteImpactSummary({
  impact,
  loading,
}: {
  impact: DirectoryDeleteImpact | undefined;
  loading: boolean;
}) {
  if (loading || !impact) {
    return <p className="text-sm text-muted-foreground">Calculating impact…</p>;
  }
  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm font-medium text-foreground">
        The following will be permanently deleted:
      </p>
      <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
        <li>
          <span className="font-medium text-foreground">{impact.contacts}</span> contacts
        </li>
        <li>
          <span className="font-medium text-foreground">{impact.agent_contacts}</span> agent
          assignments
        </li>
        <li>
          <span className="font-medium text-foreground">{impact.scheduled_calls}</span> scheduled
          calls
        </li>
      </ul>
      <p className="text-sm text-muted-foreground">
        <span className="font-medium text-foreground">{impact.syncs_detached}</span> sync
        {impact.syncs_detached === 1 ? '' : 's'} will be detached (kept for audit). Reusable schemas
        are kept.
      </p>
    </div>
  );
}
