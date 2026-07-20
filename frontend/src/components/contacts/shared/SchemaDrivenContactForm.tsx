'use client';

import { Controller, type Control, type FieldValues, type Path } from 'react-hook-form';

import { CheckboxField, SelectInput, TextInput } from '@/components/shared';
import type { SchemaField } from '@/types/contactSchema';

/**
 * Renders the inputs for a single contact from a schema's `schema_fields` (RHF-driven).
 *
 * WHAT: draws the fixed `name` + `phone_number` inputs plus one input per ACTIVE schema
 * field (string/number → `TextInput`, `enum` → `SelectInput`, `boolean` → `CheckboxField`),
 * bound to `contact_metadata.<field_name>`. Extracted verbatim from the old
 * `ContactFormModal` inline logic so Add + Edit + multi-row add all share it.
 *
 * WHEN: mount inside any RHF form whose schema was built with `buildContactFormSchema`.
 * Pass the form `control` and, for multi-row add, a `namePrefix` (e.g. `rows.0`) so the
 * field paths nest correctly. Validation errors render inline via the shared inputs.
 *
 * The form's Zod schema owns validation — this component only renders inputs.
 */
export interface SchemaDrivenContactFormProps<TValues extends FieldValues> {
  /** The RHF control for the parent form. */
  control: Control<TValues>;
  /** The schema fields to render (only `is_active` fields are drawn). */
  fields: SchemaField[];
  /**
   * Optional dotted path prefix for the three field groups when this form is one row of
   * a multi-row add (e.g. `rows.0` → `rows.0.name`, `rows.0.metadata.<key>`). Defaults to
   * the top level (`name`, `phone_number`, `metadata.<key>`).
   */
  namePrefix?: string;
  /** Hide the fixed name/phone inputs (e.g. when the parent renders them itself). */
  hideBaseFields?: boolean;
}

export default function SchemaDrivenContactForm<TValues extends FieldValues>({
  control,
  fields,
  namePrefix,
  hideBaseFields = false,
}: SchemaDrivenContactFormProps<TValues>) {
  const prefix = namePrefix ? `${namePrefix}.` : '';
  const path = (segment: string) => `${prefix}${segment}` as Path<TValues>;
  const activeFields = fields.filter((f) => f.is_active);

  return (
    <div className="flex flex-col gap-4">
      {!hideBaseFields && (
        <>
          <TextInput name={path('name')} label="Name" control={control} placeholder="Jane Doe" />
          <TextInput
            name={path('phone_number')}
            label="Phone number"
            control={control}
            placeholder="+14155550123"
          />
        </>
      )}

      {activeFields.map((f) => {
        const fieldName = path(`metadata.${f.field_name}`);
        const fieldLabel = f.label || f.field_name;

        if (f.type === 'boolean') {
          return (
            <Controller
              key={f.id}
              name={fieldName}
              control={control}
              render={({ field }) => (
                <CheckboxField
                  id={`cf-${f.id}`}
                  label={fieldLabel}
                  isRequired={f.is_mandatory}
                  checked={!!field.value}
                  onCheckedChange={(v) => field.onChange(!!v)}
                />
              )}
            />
          );
        }

        if (f.type === 'enum') {
          return (
            <Controller
              key={f.id}
              name={fieldName}
              control={control}
              render={({ field, fieldState }) => (
                <SelectInput
                  name={f.field_name}
                  label={fieldLabel}
                  isRequired={f.is_mandatory}
                  options={(f.options ?? []).map((o) => ({
                    value: o.value,
                    label: o.label || o.value,
                  }))}
                  value={(field.value as string) ?? ''}
                  onValueChange={field.onChange}
                  error={!!fieldState.error}
                  helperText={fieldState.error?.message}
                />
              )}
            />
          );
        }

        return (
          <TextInput
            key={f.id}
            name={fieldName}
            label={fieldLabel}
            isRequired={f.is_mandatory}
            control={control}
            type={f.type === 'string' ? 'text' : 'number'}
          />
        );
      })}
    </div>
  );
}
