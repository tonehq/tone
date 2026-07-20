'use client';

import { ChevronRight, Folder, Loader2 } from 'lucide-react';
import { Checkbox as CheckboxPrimitive } from 'radix-ui';
import { useMemo, useState } from 'react';

import { useContactsList } from '@/lib/api/contacts';
import { useDirectoriesList } from '@/lib/api/contactDirectories';
import { CustomButton, SearchBar } from '@/components/shared';
import type { ContactDirectoryListItem } from '@/types/contactDirectory';
import { cn } from '@/utils/cn';

import type {
  DirectorySelectionMeta,
  TreeCheckState,
  UseDirectoryContactTreeSelectionResult,
} from './useDirectoryContactTreeSelection';

/**
 * Hierarchical tri-state directory → contacts tree-select (the "Assign from directories"
 * option). Each directory is a collapsible parent row (chevron + tri-state checkbox +
 * folder icon + name + contact-count badge); expanding it lazy-loads that directory's
 * contacts as child rows (checkbox + name/phone). Checking a directory selects ALL its
 * contacts; ticking only some children shows the parent as indeterminate. An empty
 * directory's parent checkbox is a disabled no-op.
 *
 * WHAT: renders the tree UI and delegates all selection bookkeeping to the
 * `useDirectoryContactTreeSelection` state passed in (so the hosting modal owns the
 * emitted `{ directory_ids, contact_ids }` and the confirm action).
 *
 * WHEN: used by `AssignContactsModal`; reusable for any directory+contact picker.
 */
export interface DirectoryContactTreeProps {
  selection: UseDirectoryContactTreeSelectionResult;
  className?: string;
}

/** Page size for the (paginated) directory list + each directory's lazy-loaded children. */
const PAGE_SIZE = 100;

export default function DirectoryContactTree({ selection, className }: DirectoryContactTreeProps) {
  const [search, setSearch] = useState('');
  const { data, isLoading } = useDirectoriesList({ search, page_size: PAGE_SIZE });
  const directories = data?.data ?? [];

  if (isLoading) {
    return (
      <div
        className={cn('flex items-center justify-center py-10 text-muted-foreground', className)}
      >
        <Loader2 className="mr-2 size-4 animate-spin" aria-hidden />
        Loading directories…
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col gap-3', className)}>
      <SearchBar
        value={search}
        onSearch={setSearch}
        placeholder="Search directories and contacts…"
        aria-label="Search directories and contacts"
      />

      {directories.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">No directories found.</p>
      ) : (
        <ul role="tree" aria-label="Directories and contacts" className="flex flex-col gap-1">
          {directories.map((dir) => (
            <DirectoryNode key={dir.id} directory={dir} search={search} selection={selection} />
          ))}
        </ul>
      )}
    </div>
  );
}

/** Radix tri-state checkbox with a dash indicator for the indeterminate state. */
function TriStateCheckbox({
  state,
  disabled,
  onToggle,
  label,
  className,
}: {
  state: TreeCheckState;
  disabled?: boolean;
  onToggle: () => void;
  label: string;
  className?: string;
}) {
  const checked = state === 'checked' ? true : state === 'indeterminate' ? 'indeterminate' : false;
  return (
    <CheckboxPrimitive.Root
      checked={checked}
      disabled={disabled}
      onCheckedChange={onToggle}
      aria-label={label}
      className={cn(
        'peer size-4 shrink-0 rounded-sm border border-primary shadow-xs outline-none transition-shadow',
        'data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground',
        'data-[state=indeterminate]:bg-primary data-[state=indeterminate]:text-primary-foreground',
        'focus-visible:ring-[2px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50',
        className,
      )}
    >
      <CheckboxPrimitive.Indicator className="grid place-content-center text-current">
        {state === 'indeterminate' ? (
          <span className="block h-0.5 w-2.5 rounded-full bg-current" aria-hidden />
        ) : (
          <svg viewBox="0 0 12 12" className="size-3" aria-hidden>
            <path
              d="M2 6l2.5 2.5L10 3"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        )}
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  );
}

/** One directory parent row + its lazily-loaded contact children. */
function DirectoryNode({
  directory,
  search,
  selection,
}: {
  directory: ContactDirectoryListItem;
  search: string;
  selection: UseDirectoryContactTreeSelectionResult;
}) {
  const [expanded, setExpanded] = useState(false);
  const isEmpty = directory.contact_count <= 0;

  // Lazy-load contacts only once the directory is expanded. Search filters children too.
  const { data, isLoading } = useContactsList(
    expanded ? directory.id : undefined,
    { search, page_size: PAGE_SIZE },
    undefined,
  );
  const contacts = useMemo(() => data?.data ?? [], [data]);
  const loadedContactIds = useMemo(() => contacts.map((c) => c.id), [contacts]);

  const meta: DirectorySelectionMeta = { contactCount: directory.contact_count };
  const state = selection.getDirectoryState(directory.id, loadedContactIds);

  // Un-ticking a child of a whole-directory pick "explodes" it into the loaded ids only,
  // so if not all contacts are loaded (>PAGE_SIZE), the unloaded ones would be silently
  // dropped. Lock per-child toggling in that case — the user can clear the whole directory
  // or narrow via search to edit individual contacts.
  const fullyLoaded = !data || contacts.length >= data.total;
  const lockChildren = selection.isDirectorySelected(directory.id) && !fullyLoaded;

  return (
    <li role="treeitem" aria-expanded={expanded} className="list-none">
      <div className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-muted/60">
        <CustomButton
          type="text"
          size="icon-xs"
          onClick={() => setExpanded((v) => !v)}
          aria-label={expanded ? `Collapse ${directory.name}` : `Expand ${directory.name}`}
          className="size-5 shrink-0 rounded text-muted-foreground hover:text-foreground"
        >
          <ChevronRight
            className={cn('size-4 transition-transform', expanded && 'rotate-90')}
            aria-hidden
          />
        </CustomButton>

        <TriStateCheckbox
          state={state}
          disabled={isEmpty}
          onToggle={() => selection.toggleDirectory(directory.id, loadedContactIds, meta)}
          label={`Select all contacts in ${directory.name}`}
        />

        <Folder className="size-4 shrink-0 text-muted-foreground" aria-hidden />

        <CustomButton
          type="text"
          onClick={() => setExpanded((v) => !v)}
          className="flex h-auto min-w-0 flex-1 items-center justify-start gap-2 p-0 text-left font-normal hover:bg-transparent"
        >
          <span className="truncate text-sm font-medium">{directory.name}</span>
          <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
            {directory.contact_count}
          </span>
        </CustomButton>
      </div>

      {expanded && (
        <ul role="group" className="ml-8 mt-1 flex max-h-56 flex-col gap-0.5 overflow-y-auto pr-1">
          {isLoading ? (
            <li className="flex items-center px-2 py-1.5 text-xs text-muted-foreground">
              <Loader2 className="mr-2 size-3.5 animate-spin" aria-hidden />
              Loading contacts…
            </li>
          ) : contacts.length === 0 ? (
            <li className="px-2 py-1.5 text-xs text-muted-foreground">No contacts.</li>
          ) : (
            contacts.map((contact) => {
              const checked =
                selection.isDirectorySelected(directory.id) ||
                selection.isContactSelected(contact.id);
              return (
                <li
                  key={contact.id}
                  role="treeitem"
                  className="flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-muted/60"
                >
                  <TriStateCheckbox
                    state={checked ? 'checked' : 'unchecked'}
                    disabled={lockChildren}
                    onToggle={() =>
                      selection.toggleContact(contact.id, directory.id, loadedContactIds)
                    }
                    label={`Select ${contact.name ?? contact.phone_number ?? 'contact'}`}
                  />
                  <span className="truncate text-sm">
                    {contact.name ?? 'Unnamed contact'}
                    {contact.phone_number && (
                      <span className="ml-2 text-xs text-muted-foreground">
                        {contact.phone_number}
                      </span>
                    )}
                  </span>
                </li>
              );
            })
          )}
          {data && data.total > contacts.length && (
            <li className="px-2 py-1">
              <CustomButton type="link" size="xs" disabled>
                Showing {contacts.length} of {data.total}
                {lockChildren
                  ? ' — whole directory selected; clear it or search to edit individual contacts'
                  : ' — refine your search to narrow'}
              </CustomButton>
            </li>
          )}
        </ul>
      )}
    </li>
  );
}
