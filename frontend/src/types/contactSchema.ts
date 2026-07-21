/**
 * ContactSchema + SchemaField types — mirrors `core/models/contact_schema.py` and
 * `core/models/schema_field.py` `to_dict()`, plus the contact-schemas router shapes.
 *
 * A `ContactSchema` is an ORG-LEVEL, reusable contact-shape template that owns a set of
 * `SchemaField` rows. A directory references one via `default_schema_id` (its manual-Add
 * form + validation shape); a sync may pick any org schema for its external→target
 * mapping.
 */

/** Primitive field types the backend accepts (`_ALLOWED_FIELD_TYPES`). */
export type SchemaFieldType = 'string' | 'number' | 'integer' | 'boolean' | 'enum';

/**
 * The constrained JSON-Schema-subset validators the backend allows. String/enum fields
 * accept `minLength`/`maxLength`/`pattern`; number/integer accept `minimum`/`maximum`.
 */
export interface SchemaFieldValidators {
  minLength?: number;
  maxLength?: number;
  pattern?: string;
  minimum?: number;
  maximum?: number;
}

/** An enum choice for a `type: 'enum'` field. */
export interface SchemaFieldOption {
  value: string;
  label?: string;
}

/** A single field within a schema (mirrors `SchemaField.to_dict()`). */
export interface SchemaField {
  id: string;
  schema_id: string;
  field_name: string;
  label: string | null;
  is_mandatory: boolean;
  type: SchemaFieldType;
  format: string | null;
  validators: SchemaFieldValidators;
  options: SchemaFieldOption[] | null;
  /** External header this field reads from when used as a sync mapping. null = identity. */
  source_key: string | null;
  field_metadata: Record<string, unknown>;
  display_order: number;
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

/** A schema as returned by list/create/update (bare `to_dict`, no fields). */
export interface ContactSchema {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

/**
 * How many directories/syncs currently point at a schema — surfaced on
 * get-detail / update / delete so the UI can warn that a change is shared.
 */
export interface SchemaReferencedBy {
  directories: number;
  syncs: number;
}

/**
 * `GET /contact-schemas/{id}` — the schema enriched with its ACTIVE fields and the
 * `referenced_by` counts (from `get_schema_detail`).
 */
export interface ContactSchemaDetail extends ContactSchema {
  fields: SchemaField[];
  referenced_by: SchemaReferencedBy;
}

/**
 * `PATCH /contact-schemas/{id}` — the updated schema plus its `referenced_by` count so
 * the caller can warn the edit is shared.
 */
export interface ContactSchemaUpdateResult extends ContactSchema {
  referenced_by: SchemaReferencedBy;
}

/** `DELETE /contact-schemas/{id}` — soft-deleted; returns the reference counts it had. */
export interface ContactSchemaDeleteResult {
  ok: boolean;
  referenced_by: SchemaReferencedBy;
}

/** Body for `POST /contact-schemas` (create; admin/owner). */
export interface CreateSchemaPayload {
  name: string;
  description?: string | null;
  is_active?: boolean;
}

/** Body for `PATCH /contact-schemas/{id}` (update; admin/owner). */
export interface UpdateSchemaPayload {
  name?: string | null;
  description?: string | null;
  is_active?: boolean;
}

/** Body for `POST /contact-schemas/{id}/fields` (create field; admin/owner). */
export interface CreateSchemaFieldPayload {
  field_name: string;
  type?: SchemaFieldType;
  label?: string | null;
  format?: string | null;
  is_mandatory?: boolean;
  validators?: SchemaFieldValidators | null;
  options?: SchemaFieldOption[] | null;
  source_key?: string | null;
  display_order?: number;
  /** Per-field config; for date/datetime fields: `{ datetime_format, timezone }`. */
  field_metadata?: Record<string, unknown> | null;
}

/** Body for `PATCH /schema-fields/{id}` (update field; admin/owner). */
export interface UpdateSchemaFieldPayload {
  label?: string | null;
  type?: SchemaFieldType;
  format?: string | null;
  is_mandatory?: boolean;
  validators?: SchemaFieldValidators | null;
  options?: SchemaFieldOption[] | null;
  source_key?: string | null;
  display_order?: number;
  is_active?: boolean;
  field_metadata?: Record<string, unknown> | null;
}
