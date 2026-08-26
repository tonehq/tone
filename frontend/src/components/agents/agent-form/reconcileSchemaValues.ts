import type { MetaDataSchemaField } from '@/types/provider';

/**
 * Return a copy of `current` with every schema-driven (non-structural) key
 * removed. Used by the LLM/TTS/STT provider dropdowns to hard-reset tuning
 * fields on provider change — carrying values across providers is unsafe
 * because parameter names, ranges, and even which parameters exist all vary
 * (e.g. Claude Opus 4.7 deprecated `temperature`, OpenAI temp max is 2 vs
 * Anthropic's 1). The caller then merges in the new provider_id / model_id.
 *
 * A model swap inside the same provider does NOT go through here — the
 * reconcile effect handles that by clamping to the new model's ranges so
 * intentional tuning survives.
 */
export function resetSchemaFields<T extends Record<string, unknown>>(
  current: T | undefined,
  structuralKeys: Set<string>,
): Partial<T> {
  const kept: Record<string, unknown> = {};
  if (current) {
    for (const key of Object.keys(current)) {
      if (structuralKeys.has(key)) kept[key] = current[key];
    }
  }
  return kept as Partial<T>;
}

/**
 * Compute the set of changes needed to make `current` comply with a new
 * provider/model `schema`.
 *
 * Callers get back a map of `{ key → nextValue }` where `nextValue === undefined`
 * means the key should be cleared (out of schema). Numeric values that fall
 * outside the schema field's `[min, max]` range are clamped so that swapping
 * models inside the same provider doesn't leave, say, max_completion_tokens
 * above the new model's ceiling. Provider swaps hard-reset via
 * `resetSchemaFields` before this ever runs.
 *
 * Model-level `meta_data` (e.g. per-model `max_completion_tokens`) overrides
 * the provider schema max on a per-field basis, matching `DynamicProviderFields`.
 *
 * Structural keys (provider_id, model_id, language, …) are never touched —
 * they're managed by the parent step's setValue calls.
 */
export function reconcileSchemaValues(
  current: Record<string, unknown>,
  schema: MetaDataSchemaField[],
  structuralKeys: Set<string>,
  modelMetaData?: Record<string, unknown> | null,
): Record<string, unknown | undefined> {
  const changes: Record<string, unknown | undefined> = {};
  const byName = new Map(schema.map((f) => [f.name, f]));

  for (const [key, value] of Object.entries(current)) {
    if (structuralKeys.has(key)) continue;

    const field = byName.get(key);
    if (!field) {
      changes[key] = undefined;
      continue;
    }

    if (value === null || value === undefined || value === '') continue;

    if (field.data_type === 'float' || field.data_type === 'integer' || field.data_type === 'int') {
      const num = typeof value === 'number' ? value : Number(value);
      if (Number.isNaN(num)) continue;

      const validator =
        typeof field.validator === 'object' && field.validator !== null ? field.validator : {};
      const min = validator.min as number | undefined;
      const modelMax =
        modelMetaData && field.name in modelMetaData
          ? (modelMetaData[field.name] as number)
          : undefined;
      const max = modelMax ?? (validator.max as number | undefined);

      let clamped = num;
      if (typeof min === 'number' && clamped < min) clamped = min;
      if (typeof max === 'number' && clamped > max) clamped = max;
      if (clamped !== num) changes[key] = clamped;
      continue;
    }

    if (field.options && field.options.length > 0) {
      if (!field.options.includes(String(value))) {
        changes[key] = undefined;
      }
    }
  }

  return changes;
}
