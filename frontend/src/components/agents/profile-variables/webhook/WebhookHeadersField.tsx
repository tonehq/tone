'use client';

import { type Control, useFieldArray, useWatch } from 'react-hook-form';

import { HttpHeadersBuilder } from '@/components/shared';
import type { WebhookConfigFormValues } from '@/schemas/agentProfileWebhook';

/** RHF bridge: drives the shared `HttpHeadersBuilder` from a `headers` field
 * array. RHF supplies each row's stable id via its own `id` key. */
export default function WebhookHeadersField({
  control,
}: {
  control: Control<WebhookConfigFormValues>;
}) {
  const { fields, append, remove, update } = useFieldArray({ control, name: 'headers' });
  const watched = useWatch({ control, name: 'headers' }) ?? [];

  return (
    <HttpHeadersBuilder
      rows={fields.map((f, i) => ({
        id: f.id,
        key: watched[i]?.key ?? '',
        value: watched[i]?.value ?? '',
      }))}
      onAdd={() => append({ key: '', value: '' })}
      onRemove={(id) => {
        const idx = fields.findIndex((f) => f.id === id);
        if (idx >= 0) remove(idx);
      }}
      onChange={(id, patch) => {
        const idx = fields.findIndex((f) => f.id === id);
        if (idx >= 0) update(idx, { ...watched[idx], ...patch });
      }}
    />
  );
}
