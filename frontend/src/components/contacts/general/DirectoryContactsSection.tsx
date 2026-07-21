'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Pencil, Plus, Trash2, Upload, Users } from 'lucide-react';
import { z } from 'zod';

import { useDirectory } from '@/lib/api/contactDirectories';
import { useSchema } from '@/lib/api/contactSchemas';
import {
  useBulkDeleteContacts,
  useContactsList,
  useDeleteContact,
  useUpdateContact,
} from '@/lib/api/contacts';
import { CustomButton, CustomModal } from '@/components/shared';
import { PhoneNumberDisplay } from '@/components/shared/PhoneNumberDisplay';
import ContactsTable from '@/components/contacts/shared/ContactsTable';
import ConfirmDeleteModal from '@/components/contacts/shared/ConfirmDeleteModal';
import SchemaDrivenContactForm from '@/components/contacts/shared/SchemaDrivenContactForm';
import UploadContactsModal from '@/components/contacts/shared/UploadContactsModal';
import { useSyncStatusPolling } from '@/components/contacts/shared/useSyncStatusPolling';
import { buildContactFormSchema } from '@/components/contacts/shared/buildContactFormSchema';
import type { Contact, ListContactsParams } from '@/types/contact';
import type { SchemaField } from '@/types/contactSchema';
import type { CustomTableColumn, CustomTableSortState } from '@/types/components';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

import AddContactsModal from './AddContactsModal';

/**
 * The "General" pane of a Contact Directory.
 *
 * WHAT: lists a directory's contacts (server search / sort / paginate via
 * `useContactsList`) with per-row edit + delete and bulk-delete; hosts the multi-row
 * "Add Contacts" modal and the shared "Upload Contacts" (CSV / Excel) modal. It drives the
 * directory's default-schema fields (fetched via the directory → schema hooks) into the
 * add / edit forms so metadata inputs match the schema. After a sync completes it shows a
 * completed-with-warnings banner (linking the error report) and refreshes the list.
 *
 * WHEN: rendered by the directory detail shell for the "General" tab.
 */
export interface DirectoryContactsSectionProps {
  directoryId: string;
}

const PAGE_SIZE = 20;

export default function DirectoryContactsSection({ directoryId }: DirectoryContactsSectionProps) {
  // Resolve the directory's default schema → its fields (drives the add / edit forms).
  const { data: directory } = useDirectory(directoryId);
  const defaultSchemaId = directory?.default_schema_id ?? null;
  const { data: schema } = useSchema(defaultSchemaId);
  const fields: SchemaField[] = useMemo(() => schema?.fields ?? [], [schema]);

  // Server-driven list params (search / sort / page).
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState<CustomTableSortState | null>(null);
  const [page, setPage] = useState(1);

  const listParams: ListContactsParams = {
    page_no: page,
    page_size: PAGE_SIZE,
    search: search || undefined,
    sort_by: sort?.field,
    sort_order: sort?.order,
  };
  const { data: contactsPage, isLoading, refetch } = useContactsList(directoryId, listParams);

  const contacts = contactsPage?.data ?? [];
  const total = contactsPage?.total ?? 0;

  // Selection for bulk-delete.
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  // Modals / dialogs.
  const [addOpen, setAddOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [editContact, setEditContact] = useState<Contact | null>(null);
  const [deleteContact, setDeleteContact] = useState<Contact | null>(null);
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false);

  // Post-sync banner: once a sync completes we pull the directory's most recent sync so we
  // can poll it (for the completed-with-warnings banner) and link its error report.
  const [lastSyncId, setLastSyncId] = useState<string | null>(null);
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const syncPoll = useSyncStatusPolling(lastSyncId);

  const deleteContactMutation = useDeleteContact(directoryId);
  const bulkDeleteMutation = useBulkDeleteContacts(directoryId);

  const isSelected = (id: string) => selectedIds.includes(id);
  const toggleSelected = (id: string) =>
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  const allOnPageSelected = contacts.length > 0 && contacts.every((c) => isSelected(c.id));
  const toggleSelectAll = () =>
    setSelectedIds((prev) =>
      allOnPageSelected
        ? prev.filter((id) => !contacts.some((c) => c.id === id))
        : Array.from(new Set([...prev, ...contacts.map((c) => c.id)])),
    );

  const columns: CustomTableColumn<Contact>[] = useMemo(
    () => [
      {
        key: 'select',
        title: (
          <input
            type="checkbox"
            aria-label="Select all contacts on this page"
            checked={allOnPageSelected}
            onChange={toggleSelectAll}
            className="size-4 cursor-pointer accent-primary"
          />
        ),
        width: '44px',
        render: (_v, record) => (
          <input
            type="checkbox"
            aria-label={`Select contact ${record.name ?? record.phone_number ?? record.id}`}
            checked={isSelected(record.id)}
            onChange={(e) => {
              e.stopPropagation();
              toggleSelected(record.id);
            }}
            onClick={(e) => e.stopPropagation()}
            className="size-4 cursor-pointer accent-primary"
          />
        ),
      },
      {
        key: 'name',
        title: 'Name',
        dataIndex: 'name',
        sorter: true,
        render: (_v, record) =>
          record.name ? (
            <span className="font-medium text-foreground">{record.name}</span>
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
      },
      {
        key: 'phone_number',
        title: 'Phone',
        dataIndex: 'phone_number',
        sorter: true,
        className: 'tabular-nums',
        render: (_v, record) =>
          record.phone_number ? (
            <PhoneNumberDisplay phoneNumber={record.phone_number} flagSize="sm" />
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
      },
      {
        key: 'actions',
        title: '',
        align: 'right',
        width: '96px',
        render: (_v, record) => (
          // Hover/focus-reveal on pointer devices; stays visible where hover is
          // unavailable (touch) so actions remain reachable. Keyboard focus reveals via
          // `focus-within`, and the buttons keep their default focus rings.
          <div className="flex items-center justify-end gap-1 opacity-100 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100 [@media(hover:hover)]:opacity-0">
            <CustomButton
              type="text"
              size="icon-xs"
              onClick={(e) => {
                e.stopPropagation();
                setEditContact(record);
              }}
              aria-label="Edit contact"
            >
              <Pencil className="size-4" aria-hidden />
            </CustomButton>
            <CustomButton
              type="text"
              size="icon-xs"
              onClick={(e) => {
                e.stopPropagation();
                setDeleteContact(record);
              }}
              aria-label="Delete contact"
            >
              <Trash2 className="size-4 text-red-600" aria-hidden />
            </CustomButton>
          </div>
        ),
      },
    ],
    // Re-derive when the current page's selection changes so the checkboxes reflect state.
    [contacts, selectedIds],
  );

  const handleSortChange = (next: CustomTableSortState | null) => {
    setSort(next);
    setPage(1);
  };

  const handleSearchChange = (value: string) => {
    setSearch(value);
    setPage(1);
  };

  const confirmDelete = async () => {
    if (!deleteContact) return;
    try {
      await deleteContactMutation.mutateAsync(deleteContact.id);
      showToast.success('Contact deleted');
      setSelectedIds((prev) => prev.filter((id) => id !== deleteContact.id));
      setDeleteContact(null);
    } catch (err) {
      handleApiError(err);
    }
  };

  const confirmBulkDelete = async () => {
    try {
      const res = await bulkDeleteMutation.mutateAsync(selectedIds);
      showToast.success(`${res.deleted} contact${res.deleted === 1 ? '' : 's'} deleted`);
      setSelectedIds([]);
      setBulkDeleteOpen(false);
    } catch (err) {
      handleApiError(err);
    }
  };

  const showBanner = !bannerDismissed && syncPoll.isTerminal && !!lastSyncId;

  return (
    <div className="flex h-full min-h-0 flex-col gap-4">
      {showBanner && (
        <SyncCompletedBanner
          warnings={syncPoll.completedWithWarnings}
          failed={syncPoll.isFailed}
          error={syncPoll.sync?.error ?? null}
          onDismiss={() => setBannerDismissed(true)}
        />
      )}

      <ContactsTable<Contact>
        columns={columns}
        data={contacts}
        rowKey="id"
        loading={isLoading}
        total={total}
        page={page}
        pageSize={PAGE_SIZE}
        onPageChange={(nextPage) => setPage(nextPage)}
        searchValue={search}
        onSearchChange={handleSearchChange}
        searchPlaceholder="Search contacts..."
        sort={sort}
        onSortChange={handleSortChange}
        fillHeight
        groupRows
        emptyState={
          <div className="flex flex-col items-center gap-3 py-10 text-center">
            <span className="flex size-12 items-center justify-center rounded-full bg-muted/60">
              <Users className="size-6 text-muted-foreground" aria-hidden />
            </span>
            <div className="flex flex-col gap-1">
              <p className="text-sm font-medium text-foreground">No contacts yet</p>
              <p className="text-xs text-muted-foreground">
                Add contacts manually or upload a CSV / Excel file to get started.
              </p>
            </div>
            <div className="mt-1 flex items-center gap-2">
              <CustomButton type="default" size="sm" onClick={() => setUploadOpen(true)}>
                <Upload className="size-4" aria-hidden />
                Upload Contacts
              </CustomButton>
              <CustomButton type="primary" size="sm" onClick={() => setAddOpen(true)}>
                <Plus className="size-4" aria-hidden />
                Add Contacts
              </CustomButton>
            </div>
          </div>
        }
        toolbar={
          <div className="flex items-center gap-2">
            {selectedIds.length > 0 && (
              <CustomButton type="default" onClick={() => setBulkDeleteOpen(true)}>
                <Trash2 className="size-4" aria-hidden />
                Delete ({selectedIds.length})
              </CustomButton>
            )}
            <CustomButton type="default" onClick={() => setUploadOpen(true)}>
              <Upload className="size-4" aria-hidden />
              Upload Contacts
            </CustomButton>
            <CustomButton type="primary" onClick={() => setAddOpen(true)}>
              <Plus className="size-4" aria-hidden />
              Add Contacts
            </CustomButton>
          </div>
        }
      />

      <AddContactsModal
        open={addOpen}
        onClose={() => setAddOpen(false)}
        directoryId={directoryId}
        defaultSchemaId={defaultSchemaId}
        onCompleted={() => refetch()}
      />

      <UploadContactsModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        directoryId={directoryId}
        defaultSchemaId={defaultSchemaId}
        onCompleted={(syncId) => {
          // The modal reports the finished sync's id directly, so the banner can poll it +
          // link its report without re-deriving it from a possibly-stale "recent sync" query.
          refetch();
          if (syncId) setLastSyncId(syncId);
          setBannerDismissed(false);
        }}
      />

      {editContact && (
        <EditContactModal
          open={!!editContact}
          contact={editContact}
          directoryId={directoryId}
          fields={fields}
          onClose={() => setEditContact(null)}
          onSaved={() => {
            setEditContact(null);
            refetch();
          }}
        />
      )}

      <ConfirmDeleteModal
        open={!!deleteContact}
        onClose={() => setDeleteContact(null)}
        onConfirm={confirmDelete}
        title="Delete contact"
        description="This contact will be permanently removed from the directory."
        loading={deleteContactMutation.isPending}
      />

      <ConfirmDeleteModal
        open={bulkDeleteOpen}
        onClose={() => setBulkDeleteOpen(false)}
        onConfirm={confirmBulkDelete}
        title="Delete contacts"
        description={`${selectedIds.length} contact${
          selectedIds.length === 1 ? '' : 's'
        } will be permanently removed from the directory.`}
        loading={bulkDeleteMutation.isPending}
      />
    </div>
  );
}

/** The post-sync banner: warnings (link the error report) or a hard-failure notice. */
function SyncCompletedBanner({
  warnings,
  failed,
  error,
  onDismiss,
}: {
  warnings: boolean;
  failed: boolean;
  error: string | null;
  onDismiss: () => void;
}) {
  if (failed) {
    return (
      <div
        role="alert"
        className="flex items-start justify-between gap-3 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-800 ring-1 ring-inset ring-red-200"
      >
        <span>{error ?? 'The last sync failed. Please check the file and try again.'}</span>
        <CustomButton type="text" size="sm" onClick={onDismiss}>
          Dismiss
        </CustomButton>
      </div>
    );
  }

  if (!warnings) {
    return (
      <div
        role="status"
        className="flex items-start justify-between gap-3 rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-800 ring-1 ring-inset ring-emerald-200"
      >
        <span>Sync completed. Contacts are up to date.</span>
        <CustomButton type="text" size="sm" onClick={onDismiss}>
          Dismiss
        </CustomButton>
      </div>
    );
  }

  return (
    <div
      role="alert"
      className="flex items-start justify-between gap-3 rounded-lg bg-orange-50 px-4 py-3 text-sm text-orange-800 ring-1 ring-inset ring-orange-200"
    >
      <span>
        Sync completed with warnings — some rows were skipped.{' '}
        <Link href="/contacts/sync-history" className="font-medium underline">
          View error report
        </Link>
      </span>
      <CustomButton type="text" size="sm" onClick={onDismiss}>
        Dismiss
      </CustomButton>
    </div>
  );
}

/** Inline single-contact edit modal (reuses the schema-driven form). */
function EditContactModal({
  open,
  contact,
  directoryId,
  fields,
  onClose,
  onSaved,
}: {
  open: boolean;
  contact: Contact;
  directoryId: string;
  fields: SchemaField[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const updateContact = useUpdateContact(directoryId);
  const formSchema = useMemo(() => buildContactFormSchema(fields), [fields]);
  type FormValues = z.infer<typeof formSchema>;

  const { control, handleSubmit } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: contact.name ?? '',
      phone_number: contact.phone_number ?? '',
      metadata: (contact.contact_metadata ?? {}) as Record<string, unknown>,
    },
  });

  const onSubmit = async (values: FormValues) => {
    try {
      await updateContact.mutateAsync({
        id: contact.id,
        payload: {
          name: values.name || null,
          phone_number: values.phone_number || null,
          contact_metadata: values.metadata,
        },
      });
      showToast.success('Contact updated');
      onSaved();
    } catch (err) {
      handleApiError(err);
    }
  };

  return (
    <CustomModal open={open} onClose={onClose} title="Edit contact" hideFooter width="sm:max-w-lg">
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
        <SchemaDrivenContactForm control={control} fields={fields} />
        <div className="flex justify-end gap-2 pt-2">
          <CustomButton type="default" onClick={onClose}>
            Cancel
          </CustomButton>
          <CustomButton type="primary" htmlType="submit" loading={updateContact.isPending}>
            Save
          </CustomButton>
        </div>
      </form>
    </CustomModal>
  );
}
