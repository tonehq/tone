'use client';

import type { Control, FieldErrors } from 'react-hook-form';

import { CheckboxField } from '@/components/shared';
import type { WebhookConfigFormValues } from '@/schemas/agentProfileWebhook';

/** Inbound / outbound toggles. Inbound runs enrichment as a call arrives;
 * outbound is supported but its failure policy (abort) is deferred. */
export default function WebhookDirectionsField({
  control,
  errors,
}: {
  control: Control<WebhookConfigFormValues>;
  errors: FieldErrors<WebhookConfigFormValues>;
}) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-6">
        <CheckboxField id="directions.inbound" control={control} label="Inbound calls" />
        <CheckboxField id="directions.outbound" control={control} label="Outbound calls" />
      </div>
      {errors.directions?.message && (
        <p className="text-xs text-destructive">{errors.directions.message}</p>
      )}
    </div>
  );
}
