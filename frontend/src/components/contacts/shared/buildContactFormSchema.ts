import { z } from 'zod';

import type { SchemaField } from '@/types/contactSchema';

/**
 * Build a runtime Zod object schema from a directory/schema's `schema_fields`.
 *
 * WHAT: mirrors the backend field rules (type + `is_mandatory` + validators) so the same
 * constraints are enforced client-side before the request. Only ACTIVE fields are used;
 * the returned schema is keyed by `field_name` (matching `contact_metadata`).
 *
 * WHEN: use it wherever contact metadata is entered against a schema — the Add and Edit
 * contact forms both compose it into their form schema (extracted from the old inline
 * `ContactFormModal.buildMetadataSchema`, now shared per the DRY catalog).
 */
/** Treat an empty/blank input as "no value" so `.optional()` and required checks behave. */
const emptyToUndefined = (v: unknown) => (v === '' || v == null ? undefined : v);

export function buildContactMetadataSchema(fields: SchemaField[]): z.ZodObject<z.ZodRawShape> {
  const shape: Record<string, z.ZodTypeAny> = {};
  for (const f of fields.filter((d) => d.is_active)) {
    let schema: z.ZodTypeAny;
    if (f.type === 'boolean') {
      schema = z.boolean().optional();
    } else if (f.type === 'enum') {
      const values = (f.options ?? []).map((o) => o.value);
      let enumSchema: z.ZodTypeAny = values.length
        ? z.enum(values as [string, ...string[]])
        : z.string();
      if (!f.is_mandatory) enumSchema = enumSchema.optional().or(z.literal(''));
      schema = enumSchema;
    } else if (f.type === 'number' || f.type === 'integer') {
      let num = z.coerce.number();
      if (f.validators.minimum != null) num = num.min(f.validators.minimum);
      if (f.validators.maximum != null) num = num.max(f.validators.maximum);
      if (f.type === 'integer') num = num.int();
      // Number inputs emit '' when cleared; `z.coerce.number('')` is 0, which would
      // silently pass a required field and store 0 for an optional one. Map empty to
      // undefined first so required stays required and optional fields are omitted.
      schema = z.preprocess(emptyToUndefined, f.is_mandatory ? num : num.optional());
    } else {
      let str = z.string();
      if (f.validators.minLength != null) str = str.min(f.validators.minLength);
      if (f.validators.maxLength != null) str = str.max(f.validators.maxLength);
      if (f.validators.pattern) str = str.regex(new RegExp(f.validators.pattern));
      // For optional fields, treat '' as absent so a `minLength` validator doesn't
      // reject a blank input (`.optional()` only admits undefined, not '').
      schema = f.is_mandatory
        ? str.min(1, `${f.label || f.field_name} is required`)
        : z.preprocess(emptyToUndefined, str.optional());
    }
    shape[f.field_name] = schema;
  }
  return z.object(shape);
}

/** E.164 phone validation shared by the contact forms (empty allowed — number optional). */
export const phoneNumberSchema = z
  .string()
  .optional()
  .refine((v) => !v || /^\+[1-9]\d{6,14}$/.test(v), 'Must be E.164 (e.g. +14155550123)');

/**
 * The full contact form schema: the fixed `name` + `phone_number` columns plus the
 * schema-driven `metadata` object. Rebuild it whenever `fields` change (memoise at the
 * call site).
 */
export function buildContactFormSchema(fields: SchemaField[]) {
  return z
    .object({
      name: z.string().optional(),
      phone_number: phoneNumberSchema,
      metadata: buildContactMetadataSchema(fields),
    })
    .refine((v) => !!(v.name?.trim() || v.phone_number?.trim()), {
      message: 'Enter a name or phone number',
      path: ['name'],
    });
}

/** Inferred value type of the contact form (name + phone + metadata record). */
export interface ContactFormValues {
  name?: string;
  phone_number?: string;
  metadata: Record<string, unknown>;
}
