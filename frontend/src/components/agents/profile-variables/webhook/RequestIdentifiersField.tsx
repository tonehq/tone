'use client';

import { Plus } from 'lucide-react';
import { type Control, useFieldArray } from 'react-hook-form';

import RequestIdentifierRow from '@/components/agents/profile-variables/webhook/RequestIdentifierRow';
import { CustomButton } from '@/components/shared';
import type { WebhookConfigFormValues } from '@/schemas/agentProfileWebhook';

/** Manages the `request_identifiers` array — what caller fields to send and
 * where. v1 ships a single `phone` row; the array shape lets email/name be
 * added later without a schema change. */
export default function RequestIdentifiersField({
  control,
}: {
  control: Control<WebhookConfigFormValues>;
}) {
  const { fields, append, remove } = useFieldArray({ control, name: 'request_identifiers' });

  return (
    <div className="space-y-2">
      {fields.map((f, index) => (
        <RequestIdentifierRow
          key={f.id}
          control={control}
          index={index}
          removable={fields.length > 1}
          onRemove={() => remove(index)}
        />
      ))}
      <CustomButton
        type="default"
        size="sm"
        fullWidth
        icon={<Plus size={12} />}
        onClick={() => append({ identifier: 'phone', param: 'phone', in: 'query' })}
        className="border-dashed text-[12px] text-muted-foreground hover:border-primary/40 hover:bg-primary/5 hover:text-foreground"
      >
        Add identifier
      </CustomButton>
    </div>
  );
}
