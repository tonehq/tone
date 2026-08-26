'use client';

import { FolderOpen } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

import { IconChip } from '@/components/shared';
import { useDirectoriesList } from '@/lib/api/contactDirectories';

/**
 * `/contacts/directories` index (right-pane host when no directory is selected).
 *
 * With no directory in the route, auto-select the first directory by redirecting
 * to `/contacts/directories/[firstId]`. If the org has no directories yet, show a
 * "Select a directory" placeholder (the rail owns the empty/create state).
 */
export default function ContactsDirectoriesIndexPage() {
  const router = useRouter();
  const { data, isLoading } = useDirectoriesList({
    page_size: 1,
    sort_by: 'name',
    sort_order: 'asc',
  });

  const firstDirectoryId = data?.data?.[0]?.id ?? null;

  useEffect(() => {
    if (firstDirectoryId) router.replace(`/contacts/directories/${firstDirectoryId}`);
  }, [firstDirectoryId, router]);

  if (isLoading || firstDirectoryId) {
    // While loading, or briefly before the redirect lands, render nothing
    // heavy — the rail already shows its own loading state.
    return null;
  }

  return (
    <div className="flex h-full w-full min-w-0 flex-col items-center justify-center gap-3 p-8 text-center">
      <IconChip
        icon={<FolderOpen strokeWidth={1.5} />}
        tone="muted"
        size="xl"
        className="rounded-full"
      />
      <p className="text-base font-semibold text-foreground">Select a directory</p>
      <p className="max-w-xs text-balance break-words text-sm text-muted-foreground">
        Choose a directory from the list, or create one to start adding contacts.
      </p>
    </div>
  );
}
