'use client';

import { FolderOpen, Plus } from 'lucide-react';
import { useMemo, useState } from 'react';

import DirectoryFormModal from '@/components/contacts/DirectoryFormModal';
import { CustomButton, CustomTooltip, SearchBar } from '@/components/shared';
import { useDirectoriesList } from '@/lib/api/contactDirectories';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/stores/auth';
import type { ContactDirectory, ContactDirectoryListItem } from '@/types/contactDirectory';

/**
 * Left rail of the Contacts master-detail shell (~300px).
 *
 * WHAT: a searchable, selectable list of the org's contact directories. Each row
 * shows the directory name (truncated + tooltip on overflow) and a live
 * contact-count badge; the active directory is highlighted with the same
 * treatment the app sidebar uses for its active item. Admins/owners get a
 * "New Directory" button; on create the new directory is selected. Empty and
 * loading (skeleton) states are handled inline.
 *
 * WHEN: rendered once by `ContactsMasterDetail` and kept mounted across detail
 * navigation so its scroll position + selection survive back-navigation.
 */
export interface ContactDirectoryRailProps {
  /** The directory id currently open in the detail pane (null on the placeholder). */
  activeDirectoryId: string | null;
  /** Navigate to a directory's detail pane. */
  onSelect: (directoryId: string) => void;
}

const ROW_BASE =
  'group flex w-full cursor-pointer items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm transition-colors';

export default function ContactDirectoryRail({
  activeDirectoryId,
  onSelect,
}: ContactDirectoryRailProps) {
  const user = useAuthStore((s) => s.user);
  const isAdminOrOwner = user?.role === 'admin' || user?.role === 'owner';

  const [search, setSearch] = useState('');
  const [createOpen, setCreateOpen] = useState(false);

  const { data, isLoading, isError } = useDirectoriesList({
    // Backend caps page_size at 100 (ListDirectoriesRequest: le=100); 200 → 422.
    search: search || undefined,
    page_size: 100,
    sort_by: 'name',
    sort_order: 'asc',
  });

  const directories = useMemo<ContactDirectoryListItem[]>(() => data?.data ?? [], [data]);

  const handleCreated = (directory: ContactDirectory) => {
    onSelect(directory.id);
  };

  return (
    <div className="flex h-full min-h-0 w-full flex-col">
      <div className="flex shrink-0 flex-col gap-3 border-b border-border px-4 py-3.5">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-[15px] font-semibold tracking-tight text-foreground">Directories</h2>
          {isAdminOrOwner && (
            <CustomButton
              type="primary"
              size="sm"
              icon={<Plus className="size-4" />}
              onClick={() => setCreateOpen(true)}
            >
              New
            </CustomButton>
          )}
        </div>
        <SearchBar
          value={search}
          onSearch={setSearch}
          placeholder="Search directories..."
          containerClassName="max-w-none"
        />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {isLoading ? (
          <RailSkeleton />
        ) : isError ? (
          <p className="px-2 py-6 text-center text-sm text-muted-foreground">
            Couldn&apos;t load directories.
          </p>
        ) : directories.length === 0 ? (
          <EmptyState
            searching={!!search}
            canCreate={isAdminOrOwner}
            onCreate={() => setCreateOpen(true)}
          />
        ) : (
          <ul className="flex flex-col gap-0.5">
            {directories.map((directory) => (
              <li key={directory.id}>
                <DirectoryRow
                  directory={directory}
                  active={directory.id === activeDirectoryId}
                  onSelect={() => onSelect(directory.id)}
                />
              </li>
            ))}
          </ul>
        )}
      </div>

      <DirectoryFormModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onSaved={handleCreated}
      />
    </div>
  );
}

function DirectoryRow({
  directory,
  active,
  onSelect,
}: {
  directory: ContactDirectoryListItem;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-current={active ? 'true' : undefined}
      className={cn(
        ROW_BASE,
        active
          ? 'bg-sidebar-accent font-medium text-foreground'
          : 'text-foreground/85 hover:bg-sidebar-accent/60',
      )}
    >
      <FolderOpen
        className={cn('size-4 shrink-0', active ? 'text-primary' : 'text-muted-foreground')}
        strokeWidth={1.75}
      />
      <CustomTooltip content={directory.name}>
        <span className="min-w-0 flex-1 truncate">{directory.name}</span>
      </CustomTooltip>
      <span
        className={cn(
          'shrink-0 rounded-full px-1.5 py-0.5 text-[11px] font-medium tabular-nums',
          active ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground',
        )}
      >
        {directory.contact_count}
      </span>
    </button>
  );
}

function EmptyState({
  searching,
  canCreate,
  onCreate,
}: {
  searching: boolean;
  canCreate: boolean;
  onCreate: () => void;
}) {
  if (searching) {
    return (
      <p className="px-2 py-6 text-center text-sm text-muted-foreground">
        No directories match your search.
      </p>
    );
  }
  return (
    <div className="flex flex-col items-center gap-3 px-4 py-10 text-center">
      <div className="flex size-12 items-center justify-center rounded-full bg-muted/60">
        <FolderOpen className="size-6 text-muted-foreground/60" strokeWidth={1.5} />
      </div>
      <div className="space-y-1">
        <p className="text-sm font-medium text-foreground">No directories yet</p>
        <p className="text-xs text-muted-foreground">Create one to start organizing contacts.</p>
      </div>
      {canCreate && (
        <CustomButton
          type="primary"
          size="sm"
          icon={<Plus className="size-4" />}
          onClick={onCreate}
        >
          Create directory
        </CustomButton>
      )}
    </div>
  );
}

function RailSkeleton() {
  return (
    <ul className="flex flex-col gap-0.5" aria-hidden>
      {Array.from({ length: 6 }).map((_, i) => (
        <li key={i} className="flex items-center gap-2 px-2.5 py-2">
          <div className="size-4 shrink-0 animate-pulse rounded bg-muted" />
          <div className="h-3.5 flex-1 animate-pulse rounded bg-muted" />
          <div className="h-4 w-6 shrink-0 animate-pulse rounded-full bg-muted" />
        </li>
      ))}
    </ul>
  );
}
