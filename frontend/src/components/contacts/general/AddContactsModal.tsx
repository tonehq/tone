'use client';

import { useEffect, useMemo, useState } from 'react';
import { useFieldArray, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Plus, Trash2 } from 'lucide-react';
import { z } from 'zod';

import { useCreateContacts } from '@/lib/api/contacts';
import { useDirectoriesList } from '@/lib/api/contactDirectories';
import { useSchema, useSchemasList } from '@/lib/api/contactSchemas';
import { CustomButton, CustomModal, SelectInput } from '@/components/shared';
import AdvancedDirectoryConfig from '@/components/contacts/shared/AdvancedDirectoryConfig';
import SchemaDrivenContactForm from '@/components/contacts/shared/SchemaDrivenContactForm';
import { buildContactFormSchema } from '@/components/contacts/shared/buildContactFormSchema';
import type { ContactRowPayload, CreateContactFailure } from '@/types/contact';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

/**
 * Multi-row "Add contact(s)" modal — shared by BOTH the directory General view and the
 * agent Contacts tab (one modal, one create endpoint).
 *
 * WHAT: renders N repeatable rows of `SchemaDrivenContactForm` (driven by the directory's
 * default-schema fields) and submits them as a bulk create. Handles the C-7 partial
 * response `{ created, failed }`: on any failures it toasts the created count and KEEPS
 * the modal open, highlighting the failed rows with their inline `errors`; it only closes
 * (and reports success) once every submitted row was created.
 *
 * TWO CONTEXTS:
 * - Directory General: pass `directoryId` (+ `defaultSchemaId`). Behaves as before — no
 *   directory picker, the schema selector stays.
 * - Agent Contacts tab: pass `agentId` and NO `directoryId`. A directory picker appears so
 *   the user chooses which directory to create the contact in; the create request carries
 *   `agent_id`, so the backend also ASSIGNS the created contacts to that agent.
 */
export interface AddContactsModalProps {
  open: boolean;
  onClose: () => void;
  /** Directory to create into (General view). Omit in the agent-tab context. */
  directoryId?: string;
  /** When set (and `directoryId` omitted), created contacts are assigned to this agent. */
  agentId?: string;
  /** The directory's default schema id — preselected in the schema picker. */
  defaultSchemaId?: string | null;
  /** Called after every submitted row lands, so the parent can refresh its list. */
  onCompleted?: () => void;
}

/** A single blank row seed (name + phone + an empty metadata bag). */
function emptyRow(): { name: string; phone_number: string; metadata: Record<string, unknown> } {
  return { name: '', phone_number: '', metadata: {} };
}

export default function AddContactsModal({
  open,
  onClose,
  directoryId,
  agentId,
  defaultSchemaId,
  onCompleted,
}: AddContactsModalProps) {
  // Agent-tab context: no fixed directory, but an agent to assign the created contacts to.
  const isAgentContext = !directoryId && !!agentId;

  // Directory picker (agent context only) — fetch a wide page so all directories are
  // selectable; the query is cheap and shared via TanStack Query.
  const directoriesQuery = useDirectoriesList({ page_size: 100 });
  const directoryOptions = (directoriesQuery.data?.data ?? []).map((d) => ({
    value: d.id,
    label: d.name,
  }));

  // The org's seeded "Global" directory is the default target in the agent context —
  // resolved BY NAME from the normal directories list (there is no /global endpoint).
  const globalDirectory = directoriesQuery.data?.data?.find((d) => d.name === 'Global');

  const [pickedDirectoryId, setPickedDirectoryId] = useState<string>('');
  // The directory we actually create into: the fixed prop, or the user's pick.
  const effectiveDirectoryId = directoryId ?? pickedDirectoryId;

  const createContacts = useCreateContacts(effectiveDirectoryId);

  const schemasQuery = useSchemasList({ page_size: 100 });
  const schemaOptions = (schemasQuery.data?.data ?? []).map((s) => ({
    value: s.id,
    label: s.name,
  }));

  const [schemaId, setSchemaId] = useState<string>(defaultSchemaId ?? '');
  const { data: schemaDetail } = useSchema(schemaId || null);
  const fields = useMemo(() => schemaDetail?.fields ?? [], [schemaDetail]);

  const formSchema = useMemo(
    () => z.object({ rows: z.array(buildContactFormSchema(fields)) }),
    [fields],
  );
  type FormValues = z.infer<typeof formSchema>;

  const { control, handleSubmit, reset } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { rows: [emptyRow()] },
  });
  const { fields: rowFields, append, remove } = useFieldArray({ control, name: 'rows' });

  const [rowErrors, setRowErrors] = useState<Record<number, string[]>>({});

  useEffect(() => {
    if (open) {
      setSchemaId(defaultSchemaId ?? '');
      // The directory is seeded by the dedicated effect below once the directories arrive,
      // so we don't touch `pickedDirectoryId` here — that would wipe typed rows when the
      // directories query resolves late.
      reset({ rows: [emptyRow()] });
      setRowErrors({});
    }
  }, [open, defaultSchemaId, reset]);

  // Once the directories list arrives (agent context), default the pick to "Global" if the
  // user hasn't chosen one yet. If no "Global" exists, the pick stays empty and the user
  // expands Advanced configuration to choose a directory.
  useEffect(() => {
    if (open && isAgentContext && !pickedDirectoryId && globalDirectory) {
      setPickedDirectoryId(globalDirectory.id);
    }
  }, [open, isAgentContext, pickedDirectoryId, globalDirectory]);

  // Changing the schema swaps the metadata field set but PRESERVES what the user already
  // typed — name/phone always apply, and any metadata for fields not in the new schema is
  // simply ignored on submit (Zod strips unknown keys), while new fields render empty.
  const handleSchemaChange = (id: string) => {
    setSchemaId(id);
    setRowErrors({});
  };

  // Agent context: picking a directory selects it and defaults the schema to that
  // directory's default schema (the user can still change it below). Entered rows are kept.
  const handleDirectoryChange = (id: string) => {
    setPickedDirectoryId(id);
    const dir = directoriesQuery.data?.data?.find((d) => d.id === id);
    setSchemaId(dir?.default_schema_id ?? '');
    setRowErrors({});
  };

  const onSubmit = async (values: FormValues) => {
    // Agent context requires a directory pick before we can create anywhere.
    if (!effectiveDirectoryId) {
      showToast.warning('Select a directory first.');
      return;
    }

    const contacts: ContactRowPayload[] = values.rows.map((row) => ({
      name: row.name || null,
      phone_number: row.phone_number || null,
      contact_metadata: row.metadata,
    }));

    try {
      // `agent_id` (when set) tells the backend to also assign the created contacts.
      const result = await createContacts.mutateAsync({ contacts, agent_id: agentId });
      const failedByIndex: Record<number, string[]> = {};
      for (const f of result.failed as CreateContactFailure[]) {
        failedByIndex[f.index] = f.errors;
      }

      if (result.created.length > 0) {
        const count = result.created.length;
        const noun = `contact${count === 1 ? '' : 's'}`;
        showToast.success(agentId ? `${count} ${noun} added & assigned` : `${count} ${noun} added`);
        onCompleted?.();
      }

      if (result.failed.length === 0) {
        onClose();
        return;
      }

      // Partial: keep the modal open, drop the created rows, keep only the failed ones so
      // the user can fix them in place, and surface each row's inline errors.
      const failedRows = values.rows
        .map((row, index) => ({ row, index }))
        .filter(({ index }) => failedByIndex[index] != null);
      reset({ rows: failedRows.map(({ row }) => row) });
      setRowErrors(
        failedRows.reduce<Record<number, string[]>>((acc, { index }, newIndex) => {
          acc[newIndex] = failedByIndex[index];
          return acc;
        }, {}),
      );
      showToast.warning(
        `${result.failed.length} row${result.failed.length === 1 ? '' : 's'} could not be added`,
      );
    } catch (err) {
      handleApiError(err);
    }
  };

  return (
    <CustomModal open={open} onClose={onClose} title="Add contacts" hideFooter width="sm:max-w-2xl">
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
        <SelectInput
          name="add-contacts-schema"
          label="Schema"
          options={schemaOptions}
          value={schemaId}
          onValueChange={handleSchemaChange}
          loading={schemasQuery.isLoading}
          placeholder="No schema — name & phone only"
        />

        <div className="flex max-h-[60vh] flex-col gap-4 overflow-y-auto pr-1">
          {rowFields.map((row, index) => (
            <div key={row.id} className="rounded-lg border border-border p-4">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-sm font-medium text-muted-foreground">
                  Contact {index + 1}
                </span>
                {rowFields.length > 1 && (
                  <CustomButton
                    type="text"
                    size="icon-xs"
                    onClick={() => {
                      remove(index);
                      setRowErrors((prev) => {
                        const next: Record<number, string[]> = {};
                        for (const [k, v] of Object.entries(prev)) {
                          const i = Number(k);
                          if (i < index) next[i] = v;
                          else if (i > index) next[i - 1] = v;
                        }
                        return next;
                      });
                    }}
                    aria-label={`Remove contact ${index + 1}`}
                  >
                    <Trash2 className="size-4" aria-hidden />
                  </CustomButton>
                )}
              </div>

              <SchemaDrivenContactForm
                control={control}
                fields={fields}
                namePrefix={`rows.${index}`}
              />

              {rowErrors[index]?.length ? (
                <ul
                  role="alert"
                  className="mt-2 list-inside list-disc rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 ring-1 ring-inset ring-red-200"
                >
                  {rowErrors[index].map((message, i) => (
                    <li key={`${index}-${i}`}>{message}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          ))}
        </div>

        <div>
          <CustomButton type="default" onClick={() => append(emptyRow())}>
            <Plus className="size-4" aria-hidden />
            Add another
          </CustomButton>
        </div>

        {isAgentContext && (
          <AdvancedDirectoryConfig
            options={directoryOptions}
            value={pickedDirectoryId}
            onChange={handleDirectoryChange}
            loading={directoriesQuery.isLoading}
          />
        )}

        <div className="flex justify-end gap-2 pt-2">
          <CustomButton type="default" onClick={onClose}>
            Cancel
          </CustomButton>
          <CustomButton
            type="primary"
            htmlType="submit"
            loading={createContacts.isPending}
            disabled={!effectiveDirectoryId}
          >
            Save contacts
          </CustomButton>
        </div>
      </form>
    </CustomModal>
  );
}
