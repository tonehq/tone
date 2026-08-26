'use client';

import { ListPlus, Pencil, Plus, Trash2, X } from 'lucide-react';
import { useState } from 'react';

import {
  useCreateSchemaField,
  useDeleteSchemaField,
  useUpdateSchemaField,
} from '@/lib/api/contactSchemas';
import {
  CheckboxField,
  CustomButton,
  IconChip,
  SelectInput,
  TextInput,
  TimezoneSelect,
} from '@/components/shared';
import { DATETIME_FORMAT_OPTIONS, DEFAULT_DATETIME_FORMAT } from '@/constants/contactSchema';
import type {
  CreateSchemaFieldPayload,
  SchemaField,
  SchemaFieldOption,
  SchemaFieldType,
} from '@/types/contactSchema';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

import ConfirmDeleteModal from './ConfirmDeleteModal';

/**
 * CRUD editor for a schema's `SchemaField` rows (type / format / required / validators /
 * enum options / source_key).
 *
 * WHAT: lists the schema's fields and provides an inline add/edit form plus per-row
 * delete (confirm). Wired to the schema-field mutation hooks (create/update/delete),
 * which invalidate the schema detail so the list refreshes. Read-only when `!canEdit`
 * (member view).
 *
 * WHEN: reuse for both a directory's default schema and any datasource schema in the
 * shared org schema library (F5). It owns only field editing — the parent owns the
 * schema-level create/rename/delete + set-as-default.
 */
/** UI-only field type. `date` / `datetime` are conveniences that persist as a string
 *  field carrying `format` = date/datetime (the backend keys date parsing off `format`,
 *  so the stored `type` stays a primitive). */
type UiFieldType = SchemaFieldType | 'date' | 'datetime';

const FIELD_TYPES: { value: UiFieldType; label: string }[] = [
  { value: 'string', label: 'Text' },
  { value: 'number', label: 'Number' },
  { value: 'integer', label: 'Integer' },
  { value: 'boolean', label: 'Boolean' },
  { value: 'enum', label: 'Enum' },
  { value: 'datetime', label: 'Date & time' },
];

// `date` is still recognised for pre-existing fields, but only `datetime` is offered as a
// new choice above (a plain date is just a datetime without a time component).
const DATETIME_TYPES = new Set<UiFieldType>(['date', 'datetime']);

export interface SchemaFieldsEditorProps {
  schemaId: string;
  fields: SchemaField[];
  /** Whether the current user may create/edit/delete fields (admin/owner). */
  canEdit?: boolean;
}

interface DraftField {
  field_name: string;
  label: string;
  type: UiFieldType;
  is_mandatory: boolean;
  source_key: string;
  /** Comma-separated enum values (only used when `type === 'enum'`). */
  optionsText: string;
  /** strptime format for date/datetime fields (e.g. `%m/%d/%Y %H:%M`); blank = ISO. */
  datetimeFormat: string;
  /** IANA source timezone for date/datetime fields; blank = UTC. */
  timezone: string;
}

const EMPTY_DRAFT: DraftField = {
  field_name: '',
  label: '',
  type: 'string',
  is_mandatory: false,
  source_key: '',
  optionsText: '',
  datetimeFormat: DEFAULT_DATETIME_FORMAT,
  timezone: '',
};

function optionsFromText(text: string): SchemaFieldOption[] {
  return text
    .split(',')
    .map((v) => v.trim())
    .filter(Boolean)
    .map((value) => ({ value }));
}

function draftToPayload(draft: DraftField): CreateSchemaFieldPayload {
  const isDatetime = DATETIME_TYPES.has(draft.type);
  return {
    field_name: draft.field_name.trim(),
    // Date / Date & time persist as a string field carrying a date/datetime `format`.
    type: isDatetime ? 'string' : (draft.type as SchemaFieldType),
    label: draft.label.trim() || null,
    format: isDatetime ? draft.type : null,
    is_mandatory: draft.is_mandatory,
    source_key: draft.source_key.trim() || null,
    options: draft.type === 'enum' ? optionsFromText(draft.optionsText) : null,
    // For date/datetime fields carry the importer parse config (a selected format + source
    // timezone); otherwise clear it.
    field_metadata: isDatetime
      ? { datetime_format: draft.datetimeFormat || null, timezone: draft.timezone || null }
      : {},
  };
}

export default function SchemaFieldsEditor({
  schemaId,
  fields,
  canEdit = false,
}: SchemaFieldsEditorProps) {
  const createField = useCreateSchemaField();
  const updateField = useUpdateSchemaField();
  const deleteField = useDeleteSchemaField();

  const [draft, setDraft] = useState<DraftField>(EMPTY_DRAFT);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<SchemaField | null>(null);

  const set = <K extends keyof DraftField>(key: K, value: DraftField[K]) =>
    setDraft((d) => ({ ...d, [key]: value }));

  const openCreate = () => {
    setEditingId(null);
    setDraft(EMPTY_DRAFT);
    setShowForm(true);
  };

  const openEdit = (field: SchemaField) => {
    setEditingId(field.id);
    const meta = (field.field_metadata ?? {}) as Record<string, unknown>;
    const isDatetime = field.format === 'date' || field.format === 'datetime';
    setDraft({
      field_name: field.field_name,
      label: field.label ?? '',
      // Surface any date/datetime-formatted string field as the "Date & time" type. `date`
      // is no longer offered as a distinct choice (see FIELD_TYPES), so a legacy `date` field
      // maps to `datetime` here — otherwise the Type selector would have no matching option
      // and render blank. The actual date-vs-datetime shape is carried by `datetimeFormat`.
      type: isDatetime ? 'datetime' : field.type,
      is_mandatory: field.is_mandatory,
      source_key: field.source_key ?? '',
      optionsText: (field.options ?? []).map((o) => o.value).join(', '),
      datetimeFormat:
        typeof meta.datetime_format === 'string' && meta.datetime_format
          ? meta.datetime_format
          : DEFAULT_DATETIME_FORMAT,
      timezone: typeof meta.timezone === 'string' ? meta.timezone : '',
    });
    setShowForm(true);
  };

  const closeForm = () => {
    setShowForm(false);
    setEditingId(null);
    setDraft(EMPTY_DRAFT);
  };

  const save = async () => {
    if (!draft.field_name.trim()) {
      showToast.error('Field name is required.');
      return;
    }
    try {
      if (editingId) {
        const { field_name: _fieldName, ...editable } = draftToPayload(draft);
        await updateField.mutateAsync({ fieldId: editingId, schemaId, payload: editable });
        showToast.success('Field updated');
      } else {
        await createField.mutateAsync({ schemaId, payload: draftToPayload(draft) });
        showToast.success('Field added');
      }
      closeForm();
    } catch (err) {
      handleApiError(err);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteField.mutateAsync({ fieldId: deleteTarget.id, schemaId });
      showToast.success('Field removed');
      setDeleteTarget(null);
    } catch (err) {
      handleApiError(err);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold">Fields</h4>
        {canEdit && !showForm && (
          <CustomButton type="default" size="sm" onClick={openCreate}>
            <Plus className="size-4" /> Add field
          </CustomButton>
        )}
      </div>

      {fields.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border px-6 py-10 text-center">
          <IconChip
            icon={<ListPlus strokeWidth={1.75} aria-hidden />}
            tone="muted"
            size="xl"
            className="rounded-full"
          />
          <div className="flex flex-col gap-1">
            <p className="text-sm font-medium text-foreground">No fields yet</p>
            <p className="text-xs text-muted-foreground">
              Add fields to define the shape of contacts using this schema.
            </p>
          </div>
          {canEdit && !showForm && (
            <CustomButton type="primary" size="sm" onClick={openCreate}>
              <Plus className="size-4" aria-hidden /> Add field
            </CustomButton>
          )}
        </div>
      ) : (
        <ul className="flex flex-col divide-y divide-border rounded-lg border border-border">
          {fields.map((field) => (
            <li key={field.id} className="flex items-center justify-between gap-3 px-3 py-2.5">
              <div className="min-w-0">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <span className="truncate">{field.label || field.field_name}</span>
                  <span className="rounded bg-muted px-1.5 py-0.5 text-[11px] text-muted-foreground">
                    {field.format === 'date' || field.format === 'datetime'
                      ? field.format
                      : field.type}
                  </span>
                  {field.is_mandatory && (
                    <span className="text-[11px] font-medium text-red-600">required</span>
                  )}
                </div>
                <p className="truncate text-xs text-muted-foreground">
                  {field.field_name}
                  {field.source_key ? ` ← ${field.source_key}` : ''}
                </p>
              </div>
              {canEdit && (
                <div className="flex items-center gap-1">
                  <CustomButton
                    type="text"
                    size="icon-xs"
                    aria-label={`Edit ${field.field_name}`}
                    onClick={() => openEdit(field)}
                  >
                    <Pencil className="size-4" />
                  </CustomButton>
                  <CustomButton
                    type="text"
                    size="icon-xs"
                    aria-label={`Delete ${field.field_name}`}
                    onClick={() => setDeleteTarget(field)}
                  >
                    <Trash2 className="size-4 text-red-600" />
                  </CustomButton>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      {canEdit && showForm && (
        <div className="flex flex-col gap-3 rounded-lg border border-border bg-muted/20 p-4">
          <div className="flex items-center justify-between">
            <h5 className="text-sm font-semibold">{editingId ? 'Edit field' : 'New field'}</h5>
            <CustomButton type="text" size="icon-xs" aria-label="Close" onClick={closeForm}>
              <X className="size-4" />
            </CustomButton>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <TextInput
              name="field_name"
              label="Field name *"
              value={draft.field_name}
              onChange={(e) => set('field_name', e.target.value)}
              disabled={!!editingId}
              placeholder="first_name"
            />
            <TextInput
              name="label"
              label="Label"
              value={draft.label}
              onChange={(e) => set('label', e.target.value)}
              placeholder="First name"
            />
            <SelectInput
              name="type"
              label="Type"
              options={FIELD_TYPES}
              value={draft.type}
              onValueChange={(v) => set('type', v as UiFieldType)}
            />
            <TextInput
              name="source_key"
              label="Source key (CSV header)"
              value={draft.source_key}
              onChange={(e) => set('source_key', e.target.value)}
              placeholder="identity if blank"
            />
            {draft.type === 'enum' && (
              <TextInput
                name="options"
                label="Options (comma-separated)"
                value={draft.optionsText}
                onChange={(e) => set('optionsText', e.target.value)}
                placeholder="low, medium, high"
              />
            )}
            {DATETIME_TYPES.has(draft.type) && (
              <>
                <TimezoneSelect
                  name="field-timezone"
                  label="Source timezone"
                  value={draft.timezone}
                  onValueChange={(v) => set('timezone', v)}
                  placeholder="UTC if blank"
                />
                <SelectInput
                  name="datetime_format"
                  label="Date/time format"
                  options={DATETIME_FORMAT_OPTIONS}
                  value={draft.datetimeFormat}
                  onValueChange={(v) => set('datetimeFormat', v)}
                />
              </>
            )}
          </div>

          <CheckboxField
            id="field-required"
            label="Required"
            checked={draft.is_mandatory}
            onCheckedChange={(v) => set('is_mandatory', !!v)}
          />

          <div className="flex justify-end gap-2">
            <CustomButton type="default" onClick={closeForm}>
              Cancel
            </CustomButton>
            <CustomButton
              type="primary"
              onClick={save}
              loading={createField.isPending || updateField.isPending}
            >
              {editingId ? 'Save' : 'Add'}
            </CustomButton>
          </div>
        </div>
      )}

      <ConfirmDeleteModal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={confirmDelete}
        title="Remove field"
        description="Existing contacts keep their metadata; the field stops being enforced."
        confirmText="Remove"
        loading={deleteField.isPending}
      />
    </div>
  );
}
