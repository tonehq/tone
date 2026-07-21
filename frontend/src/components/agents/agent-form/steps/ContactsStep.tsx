'use client';

import { Plus, Trash2, Upload, UserPlus, Users } from 'lucide-react';
import { useMemo, useState } from 'react';

import { useAgentContactsList, useUnassignContacts } from '@/lib/api/agentContacts';
import { CustomButton } from '@/components/shared';
import AddContactsModal from '@/components/contacts/general/AddContactsModal';
import AssignContactsModal from '@/components/contacts/shared/AssignContactsModal';
import ConfirmDeleteModal from '@/components/contacts/shared/ConfirmDeleteModal';
import ContactsTable from '@/components/contacts/shared/ContactsTable';
import UploadContactsModal from '@/components/contacts/shared/UploadContactsModal';
import type { AgentContactRow } from '@/types/agentContact';
import type { CustomTableColumn } from '@/types/components';
import type { PaginatedListParams } from '@/types/contactList';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

export default function ContactsStep({ agentId }: { agentId: string | null }) {
  const [params, setParams] = useState<PaginatedListParams>({ page_no: 1, page_size: 10 });
  const [assignOpen, setAssignOpen] = useState(false);
  const [addContactOpen, setAddContactOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [unassignTarget, setUnassignTarget] = useState<AgentContactRow | null>(null);

  const { data, isLoading, refetch } = useAgentContactsList(agentId, params);
  const unassign = useUnassignContacts(agentId ?? '');

  const columns = useMemo<CustomTableColumn<AgentContactRow>[]>(
    () => [
      {
        key: 'name',
        title: 'Name',
        dataIndex: 'name',
        render: (_v, row) => row.name ?? <span className="text-muted-foreground">—</span>,
      },
      {
        key: 'phone_number',
        title: 'Phone',
        dataIndex: 'phone_number',
        render: (_v, row) => row.phone_number ?? <span className="text-muted-foreground">—</span>,
      },
      {
        key: 'actions',
        title: '',
        align: 'right',
        render: (_v, row) => (
          <CustomButton
            type="text"
            size="icon-sm"
            aria-label={`Unassign ${row.name ?? row.phone_number ?? 'contact'}`}
            onClick={() => setUnassignTarget(row)}
            icon={<Trash2 className="size-4 text-muted-foreground" />}
          />
        ),
      },
    ],
    [],
  );

  if (!agentId) return null;

  const rows = data?.data ?? [];
  const total = data?.total ?? 0;

  const confirmUnassign = async () => {
    if (!unassignTarget) return;
    try {
      await unassign.mutateAsync([unassignTarget.id]);
      showToast.success('Contact unassigned.');
      setUnassignTarget(null);
      refetch();
    } catch (err) {
      handleApiError(err);
    }
  };

  return (
    <div className="flex h-full min-h-0 flex-col gap-4">
      <ContactsTable<AgentContactRow>
        columns={columns}
        data={rows}
        rowKey={(row) => row.assignment_id}
        loading={isLoading}
        total={total}
        page={params.page_no ?? 1}
        pageSize={params.page_size ?? 10}
        onPageChange={(page, pageSize) =>
          setParams((p) => ({ ...p, page_no: page, page_size: pageSize }))
        }
        searchValue={params.search ?? ''}
        onSearchChange={(search) => setParams((p) => ({ ...p, search, page_no: 1 }))}
        searchPlaceholder="Search assigned contacts…"
        sort={params.sort_by ? { field: params.sort_by, order: params.sort_order ?? 'asc' } : null}
        onSortChange={(sort) =>
          setParams((p) => ({
            ...p,
            sort_by: sort?.field,
            sort_order: sort?.order,
            page_no: 1,
          }))
        }
        emptyState={
          <div className="flex flex-col items-center gap-2 py-10 text-center">
            <Users className="size-8 text-muted-foreground" aria-hidden />
            <p className="text-sm font-medium">No contacts assigned</p>
            <p className="text-xs text-muted-foreground">
              Assign contacts from a directory or upload a CSV / Excel file to get started.
            </p>
          </div>
        }
        toolbar={
          <div className="flex items-center gap-2">
            <CustomButton
              type="default"
              size="sm"
              icon={<Plus className="size-4" />}
              onClick={() => setAddContactOpen(true)}
            >
              Add contacts
            </CustomButton>
            <CustomButton
              type="default"
              size="sm"
              icon={<Upload className="size-4" />}
              onClick={() => setUploadOpen(true)}
            >
              Upload contacts
            </CustomButton>
            <CustomButton
              type="primary"
              size="sm"
              icon={<UserPlus className="size-4" />}
              onClick={() => setAssignOpen(true)}
            >
              Assign contacts
            </CustomButton>
          </div>
        }
      />

      <AssignContactsModal
        open={assignOpen}
        onClose={() => setAssignOpen(false)}
        agentId={agentId}
        onAssigned={() => refetch()}
      />

      <AddContactsModal
        open={addContactOpen}
        onClose={() => setAddContactOpen(false)}
        agentId={agentId}
        onCompleted={() => refetch()}
      />

      <UploadContactsModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        agentId={agentId}
        onCompleted={() => refetch()}
      />

      <ConfirmDeleteModal
        open={!!unassignTarget}
        onClose={() => setUnassignTarget(null)}
        onConfirm={confirmUnassign}
        title="Unassign contact"
        description="This removes the contact from this agent. The contact itself is not deleted."
        confirmText="Unassign"
        loading={unassign.isPending}
      />
    </div>
  );
}
