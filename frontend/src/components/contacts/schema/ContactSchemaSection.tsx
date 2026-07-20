'use client';

import { useAtom, useSetAtom } from 'jotai';
import { AlertTriangle, Check, Pencil, Plus, Rows3, Star, Trash2 } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { authAtom, getCurrentUserAtom } from '@/atoms/AuthAtom';
import { useDirectory, useUpdateDirectory } from '@/lib/api/contactDirectories';
import {
  useCreateSchema,
  useDeleteSchema,
  useSchema,
  useSchemasList,
  useUpdateSchema,
} from '@/lib/api/contactSchemas';
import {
  AppLoader,
  CustomButton,
  CustomModal,
  SearchBar,
  TextAreaField,
  TextInput,
} from '@/components/shared';
import type {
  ContactSchema,
  CreateSchemaPayload,
  SchemaReferencedBy,
  UpdateSchemaPayload,
} from '@/types/contactSchema';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

import SchemaFieldsEditor from '../shared/SchemaFieldsEditor';
import ConfirmDeleteModal from '../shared/ConfirmDeleteModal';

/**
 * Datasource Schema library — the shared ORG-LEVEL contact-schema manager.
 *
 * WHAT: lists every reusable org schema (create / rename / delete) and opens the shared
 * {@link SchemaFieldsEditor} for the selected schema's fields. Because schemas are
 * org-level and reusable, edits/deletes surface a "referenced by N directories / M syncs"
 * warning (from the schema detail's `referenced_by`), and deleting a schema that is some
 * directory's default is blocked by the backend (409) — surfaced via toast.
 *
 * WHEN: rendered standalone on the `/contacts/datasource` page (no `directoryId`)
 * as a pure org-level library. When a `directoryId` is passed, it additionally exposes a
 * "set as this directory's default" control writing to that directory's `default_schema_id`.
 * Members see everything read-only; create/edit/delete + set-default are admin/owner only.
 */
export interface ContactSchemaSectionProps {
  /**
   * Optional. When set, the section also renders a "set as this directory's default"
   * control that writes to the directory's `default_schema_id`. Omit for the pure
   * org-level library (`/contacts/datasource` page).
   */
  directoryId?: string;
}

type SchemaFormMode = { kind: 'create' } | { kind: 'edit'; schema: ContactSchema };

interface SchemaFormValues {
  name: string;
  description: string;
}

const EMPTY_FORM: SchemaFormValues = { name: '', description: '' };

/** Human summary of how many directories/syncs point at a schema (empty when none). */
function referencedBySummary(ref: SchemaReferencedBy | undefined): string | null {
  if (!ref) return null;
  const parts: string[] = [];
  if (ref.directories > 0) {
    parts.push(`${ref.directories} director${ref.directories === 1 ? 'y' : 'ies'}`);
  }
  if (ref.syncs > 0) parts.push(`${ref.syncs} sync${ref.syncs === 1 ? '' : 's'}`);
  if (parts.length === 0) return null;
  return `Referenced by ${parts.join(' and ')} — edits affect all of them.`;
}

export default function ContactSchemaSection({ directoryId }: ContactSchemaSectionProps) {
  // --- current-user role (admin/owner gate) — same pattern as userMenu.tsx ---
  const [authState] = useAtom(authAtom);
  const getCurrentUser = useSetAtom(getCurrentUserAtom);
  useEffect(() => {
    if (!authState.user && !authState.isLoading) getCurrentUser();
  }, [authState.user, authState.isLoading, getCurrentUser]);
  const role = authState.user?.role;
  const canEdit = role === 'admin' || role === 'owner';

  // --- data ---
  const [search, setSearch] = useState('');
  const schemasQuery = useSchemasList({ search: search || undefined, page_size: 100 });
  const schemas = useMemo(() => schemasQuery.data?.data ?? [], [schemasQuery.data]);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  // Keep a valid selection: auto-select the first schema, clear if it disappears.
  useEffect(() => {
    if (schemas.length === 0) {
      if (selectedId !== null) setSelectedId(null);
      return;
    }
    if (!selectedId || !schemas.some((s) => s.id === selectedId)) {
      setSelectedId(schemas[0].id);
    }
  }, [schemas, selectedId]);

  const schemaDetailQuery = useSchema(selectedId);
  const schemaDetail = schemaDetailQuery.data;

  // Only fetch the directory when one is provided (the per-directory set-default control).
  const directoryQuery = useDirectory(directoryId ?? null);
  const defaultSchemaId = directoryQuery.data?.default_schema_id ?? null;

  // --- mutations ---
  const createSchema = useCreateSchema();
  const updateSchema = useUpdateSchema();
  const deleteSchema = useDeleteSchema();
  const updateDirectory = useUpdateDirectory();

  const [formMode, setFormMode] = useState<SchemaFormMode | null>(null);
  const [formValues, setFormValues] = useState<SchemaFormValues>(EMPTY_FORM);
  const [deleteTarget, setDeleteTarget] = useState<ContactSchema | null>(null);

  const openCreate = () => {
    setFormMode({ kind: 'create' });
    setFormValues(EMPTY_FORM);
  };

  const openEdit = (schema: ContactSchema) => {
    setFormMode({ kind: 'edit', schema });
    setFormValues({ name: schema.name, description: schema.description ?? '' });
  };

  const closeForm = () => {
    setFormMode(null);
    setFormValues(EMPTY_FORM);
  };

  const saveForm = async () => {
    const name = formValues.name.trim();
    if (!name) {
      showToast.error('Schema name is required.');
      return;
    }
    try {
      if (formMode?.kind === 'edit') {
        const payload: UpdateSchemaPayload = {
          name,
          description: formValues.description.trim() || null,
        };
        await updateSchema.mutateAsync({ id: formMode.schema.id, payload });
        showToast.success('Schema updated');
      } else {
        const payload: CreateSchemaPayload = {
          name,
          description: formValues.description.trim() || null,
        };
        const created = await createSchema.mutateAsync(payload);
        setSelectedId(created.id);
        showToast.success('Schema created');
      }
      closeForm();
    } catch (err) {
      handleApiError(err);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteSchema.mutateAsync(deleteTarget.id);
      showToast.success('Schema deleted');
      if (selectedId === deleteTarget.id) setSelectedId(null);
      setDeleteTarget(null);
    } catch (err) {
      // Deleting a schema that is a directory's default is blocked by the backend (409);
      // handleApiError surfaces the backend's `detail` message via toast.
      handleApiError(err);
    }
  };

  const setAsDefault = async (schemaId: string) => {
    if (!directoryId) return;
    try {
      await updateDirectory.mutateAsync({
        id: directoryId,
        payload: { default_schema_id: schemaId },
      });
      showToast.success('Set as this directory’s default schema');
    } catch (err) {
      handleApiError(err);
    }
  };

  // Reference counts for the currently-open detail — drives the shared-edit warning
  // and the delete-confirm impact copy.
  const detailReferencedBy =
    schemaDetail && selectedId === schemaDetail.id ? schemaDetail.referenced_by : undefined;
  const sharedWarning = referencedBySummary(detailReferencedBy);

  // --- render states for the schema library ---
  const renderLibrary = () => {
    if (schemasQuery.isLoading) {
      return (
        <div className="flex justify-center py-10">
          <AppLoader />
        </div>
      );
    }
    if (schemasQuery.isError) {
      return (
        <div className="flex flex-col items-center gap-3 py-10 text-center">
          <p className="text-sm text-muted-foreground">Could not load schemas.</p>
          <CustomButton type="default" size="sm" onClick={() => schemasQuery.refetch()}>
            Retry
          </CustomButton>
        </div>
      );
    }
    if (schemas.length === 0) {
      return (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border px-6 py-10 text-center">
          <span className="flex size-12 items-center justify-center rounded-full bg-muted/60">
            <Rows3 className="size-6 text-muted-foreground" aria-hidden />
          </span>
          <div className="flex flex-col gap-1">
            <p className="text-sm font-medium text-foreground">
              {search ? 'No matching schemas' : 'No schemas yet'}
            </p>
            <p className="text-xs text-muted-foreground">
              {search
                ? 'Try a different search term.'
                : 'Create a reusable schema to define contact fields once and share it.'}
            </p>
          </div>
          {canEdit && !search && (
            <CustomButton type="primary" size="sm" onClick={openCreate}>
              <Plus className="size-4" /> New schema
            </CustomButton>
          )}
        </div>
      );
    }
    return (
      <ul className="flex flex-col gap-1.5">
        {schemas.map((schema) => {
          const isSelected = schema.id === selectedId;
          const isDefault = schema.id === defaultSchemaId;
          return (
            <li key={schema.id}>
              {/* A div (not a button) so the Edit/Delete CustomButtons below aren't
                  nested buttons (invalid DOM / hydration mismatch). */}
              <div
                role="button"
                tabIndex={0}
                onClick={() => setSelectedId(schema.id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setSelectedId(schema.id);
                  }
                }}
                aria-current={isSelected}
                className={`group flex w-full cursor-pointer items-center gap-2 rounded-lg border px-3 py-2.5 text-left transition-colors ${
                  isSelected
                    ? 'border-primary bg-primary/5 ring-1 ring-primary/40'
                    : 'border-border hover:border-border hover:bg-muted/40'
                }`}
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-sm font-medium">{schema.name}</span>
                    {isDefault && (
                      <span className="inline-flex shrink-0 items-center gap-1 rounded bg-primary/10 px-1.5 py-0.5 text-[11px] font-medium text-primary">
                        <Star className="size-3" /> Default
                      </span>
                    )}
                  </div>
                  {schema.description && (
                    <p className="truncate text-xs text-muted-foreground">{schema.description}</p>
                  )}
                </div>
                {canEdit && (
                  <span className="flex shrink-0 items-center gap-1">
                    <CustomButton
                      type="text"
                      size="icon-xs"
                      aria-label={`Edit ${schema.name}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        openEdit(schema);
                      }}
                    >
                      <Pencil className="size-4" />
                    </CustomButton>
                    <CustomButton
                      type="text"
                      size="icon-xs"
                      aria-label={`Delete ${schema.name}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteTarget(schema);
                      }}
                    >
                      <Trash2 className="size-4 text-red-600" />
                    </CustomButton>
                  </span>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    );
  };

  // --- render the fields editor for the selected schema ---
  const renderDetail = () => {
    if (!selectedId) {
      return (
        <div className="flex h-full items-center justify-center py-10 text-center text-sm text-muted-foreground">
          Select a schema to view its fields.
        </div>
      );
    }
    if (schemaDetailQuery.isLoading) {
      return (
        <div className="flex justify-center py-10">
          <AppLoader />
        </div>
      );
    }
    if (schemaDetailQuery.isError || !schemaDetail) {
      return (
        <div className="flex flex-col items-center gap-3 py-10 text-center">
          <p className="text-sm text-muted-foreground">Could not load this schema.</p>
          <CustomButton type="default" size="sm" onClick={() => schemaDetailQuery.refetch()}>
            Retry
          </CustomButton>
        </div>
      );
    }

    const isDefault = schemaDetail.id === defaultSchemaId;
    return (
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="truncate text-base font-semibold">{schemaDetail.name}</h3>
            {schemaDetail.description && (
              <p className="text-sm text-muted-foreground">{schemaDetail.description}</p>
            )}
          </div>
          {canEdit &&
            directoryId &&
            (isDefault ? (
              <span className="inline-flex items-center gap-1 rounded-md bg-primary/10 px-2.5 py-1.5 text-xs font-medium text-primary">
                <Check className="size-4" /> This directory&rsquo;s default
              </span>
            ) : (
              <CustomButton
                type="default"
                size="sm"
                onClick={() => setAsDefault(schemaDetail.id)}
                loading={updateDirectory.isPending}
              >
                <Star className="size-4" /> Set as this directory&rsquo;s default
              </CustomButton>
            ))}
        </div>

        {sharedWarning && (
          <div className="flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2.5 text-sm text-amber-800 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-200">
            <AlertTriangle className="mt-0.5 size-4 shrink-0" />
            <span>{sharedWarning} Existing contacts are not re-validated.</span>
          </div>
        )}

        <SchemaFieldsEditor
          schemaId={schemaDetail.id}
          fields={schemaDetail.fields}
          canEdit={canEdit}
        />
      </div>
    );
  };

  return (
    <div className="flex h-full min-h-0 flex-col gap-4">
      <div className="flex min-h-0 flex-1 flex-col gap-4 lg:flex-row lg:items-stretch lg:gap-6">
        {/* Left: org schema library */}
        <div className="flex w-full shrink-0 flex-col gap-3 lg:w-80">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold">Schemas</h2>
            {canEdit && (
              <CustomButton type="primary" size="sm" onClick={openCreate}>
                <Plus className="size-4" /> New
              </CustomButton>
            )}
          </div>
          <SearchBar
            value={search}
            onSearch={setSearch}
            placeholder="Search schemas"
            aria-label="Search schemas"
          />
          <div className="min-h-0 flex-1 overflow-y-auto">{renderLibrary()}</div>
        </div>

        {/* Right: selected schema's fields */}
        <div className="min-h-0 min-w-0 flex-1 overflow-y-auto rounded-lg border border-border bg-card p-4">
          {renderDetail()}
        </div>
      </div>

      {/* Create / edit schema modal */}
      <CustomModal
        open={formMode !== null}
        onClose={closeForm}
        title={formMode?.kind === 'edit' ? 'Edit schema' : 'New schema'}
        confirmText={formMode?.kind === 'edit' ? 'Save' : 'Create'}
        confirmLoading={createSchema.isPending || updateSchema.isPending}
        onConfirm={saveForm}
        width="sm:max-w-md"
      >
        <div className="flex flex-col gap-4">
          {formMode?.kind === 'edit' && referencedBySummary(detailReferencedBy) && (
            <div className="flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2.5 text-sm text-amber-800 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-200">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" />
              <span>{referencedBySummary(detailReferencedBy)}</span>
            </div>
          )}
          <TextInput
            name="schema-name"
            label="Name *"
            value={formValues.name}
            onChange={(e) => setFormValues((v) => ({ ...v, name: e.target.value }))}
            placeholder="e.g. Sales leads"
          />
          <TextAreaField
            name="schema-description"
            label="Description"
            value={formValues.description}
            onChange={(e) => setFormValues((v) => ({ ...v, description: e.target.value }))}
            placeholder="What this schema is for (optional)"
          />
        </div>
      </CustomModal>

      {/* Delete schema confirm */}
      <ConfirmDeleteModal
        open={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        onConfirm={confirmDelete}
        title="Delete schema"
        description="This removes the reusable schema from your organization."
        impact={
          deleteTarget &&
          deleteTarget.id === selectedId &&
          referencedBySummary(detailReferencedBy) ? (
            <span>
              {referencedBySummary(detailReferencedBy)} A schema that is a directory&rsquo;s default
              cannot be deleted until another default is set.
            </span>
          ) : (
            'A schema that is a directory’s default cannot be deleted until another default is set.'
          )
        }
        confirmText="Delete"
        loading={deleteSchema.isPending}
      />
    </div>
  );
}
