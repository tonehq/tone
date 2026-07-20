'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { CustomModal, SelectInput, TextAreaField, TextInput } from '@/components/shared';
import { useCreateDirectory, useUpdateDirectory } from '@/lib/api/contactDirectories';
import { useSchemasList } from '@/lib/api/contactSchemas';
import type { SelectOption } from '@/types/components';
import type { ContactDirectory, UpdateDirectoryPayload } from '@/types/contactDirectory';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

/**
 * Create/edit form for a contact directory (name + description).
 *
 * WHAT: RHF + Zod modal that creates a new directory (from the rail's "New
 * Directory" button) or edits an existing one (from the detail header's edit
 * action). On success it invalidates the directory list/detail via the shared
 * mutation hooks and fires a toast; the parent decides what to do next
 * (`onSaved` receives the persisted directory — e.g. to navigate to a new one).
 *
 * WHEN: use for every directory create/edit surface so the validation + copy +
 * toast handling stays in one place.
 */
const directoryFormSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, 'Name is required')
    .max(120, 'Name must be 120 characters or fewer'),
  description: z.string().trim().max(500, 'Description must be 500 characters or fewer').optional(),
  // Optional org schema to use as this directory's default shape. No schema is
  // auto-created per directory, so leaving this empty is fine (the directory just
  // has no default until one is assigned).
  default_schema_id: z.string().optional(),
});

type DirectoryFormValues = z.infer<typeof directoryFormSchema>;

export interface DirectoryFormModalProps {
  open: boolean;
  onClose: () => void;
  /** When set, the modal is in edit mode and pre-fills from this directory. */
  directory?: ContactDirectory | null;
  /** Called after a successful create/update with the persisted directory. */
  onSaved?: (directory: ContactDirectory) => void;
}

export default function DirectoryFormModal({
  open,
  onClose,
  directory,
  onSaved,
}: DirectoryFormModalProps) {
  const isEdit = !!directory;
  const createDirectory = useCreateDirectory();
  const updateDirectory = useUpdateDirectory();
  const saving = createDirectory.isPending || updateDirectory.isPending;

  // Org-level schemas the directory can pick as its default shape.
  const schemasQuery = useSchemasList({ page_size: 100 });
  const schemaOptions: SelectOption[] = (schemasQuery.data?.data ?? []).map((s) => ({
    value: s.id,
    label: s.name,
  }));

  const {
    control,
    handleSubmit,
    reset,
    formState: { isValid },
  } = useForm<DirectoryFormValues>({
    resolver: zodResolver(directoryFormSchema),
    mode: 'onBlur',
    defaultValues: { name: '', description: '', default_schema_id: '' },
  });

  // Re-seed the form each time the modal opens (or the target directory
  // changes) so edit mode pre-fills and create mode starts clean.
  useEffect(() => {
    if (!open) return;
    reset({
      name: directory?.name ?? '',
      description: directory?.description ?? '',
      default_schema_id: directory?.default_schema_id ?? '',
    });
  }, [open, directory, reset]);

  const onSubmit = handleSubmit(async (values) => {
    const name = values.name.trim();
    const description = values.description?.trim() ? values.description.trim() : null;
    // Only send default_schema_id when the user picked one — on create the backend
    // auto-provisions a default if omitted; on edit an empty value means "leave as-is".
    const defaultSchemaId = values.default_schema_id?.trim() || null;
    try {
      let saved: ContactDirectory;
      if (isEdit) {
        const payload: UpdateDirectoryPayload = { name, description };
        if (defaultSchemaId) payload.default_schema_id = defaultSchemaId;
        saved = await updateDirectory.mutateAsync({ id: directory!.id, payload });
      } else {
        // No schema is auto-created; the user's optional pick is sent on create.
        saved = await createDirectory.mutateAsync({
          name,
          description,
          default_schema_id: defaultSchemaId,
        });
      }
      showToast.success(
        isEdit ? 'Directory updated' : 'Directory created',
        `"${saved.name}" was ${isEdit ? 'updated' : 'created'}.`,
      );
      onSaved?.(saved);
      onClose();
    } catch (error) {
      handleApiError(error);
    }
  });

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Edit directory' : 'New directory'}
      description={
        isEdit
          ? 'Update the name or description of this directory.'
          : 'Create a directory to organize contacts and their datasource schema.'
      }
      confirmText={isEdit ? 'Save changes' : 'Create directory'}
      confirmLoading={saving}
      confirmDisabled={!isValid}
      onConfirm={onSubmit}
      width="sm:max-w-md"
    >
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <TextInput
          control={control}
          name="name"
          label="Name"
          placeholder="e.g. Q3 Leads"
          autoFocus
        />
        <TextAreaField
          control={control}
          name="description"
          label="Description"
          placeholder="Optional — what this directory is for"
          rows={3}
        />
        <SelectInput
          control={control}
          name="default_schema_id"
          label="Default schema (optional)"
          placeholder={schemasQuery.isLoading ? 'Loading schemas…' : 'None — assign a schema later'}
          options={schemaOptions}
          loading={schemasQuery.isLoading}
        />
      </form>
    </CustomModal>
  );
}
