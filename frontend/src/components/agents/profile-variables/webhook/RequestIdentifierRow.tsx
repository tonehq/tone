'use client';

import { Trash2 } from 'lucide-react';
import type { Control } from 'react-hook-form';

import { CustomButton, SelectInput, TextInput } from '@/components/shared';
import { REQUEST_IDENTIFIER_IN_OPTIONS } from '@/constants/profileWebhook';
import type { WebhookConfigFormValues } from '@/schemas/agentProfileWebhook';

interface Props {
  control: Control<WebhookConfigFormValues>;
  index: number;
  onRemove: () => void;
  removable: boolean;
}

/** One request-identifier row: a fixed "phone" identifier, the param name to
 * send it under, and where (query / body). */
export default function RequestIdentifierRow({ control, index, onRemove, removable }: Props) {
  return (
    <div className="group flex items-start gap-2 rounded-lg border border-border/60 bg-card p-3">
      <div className="grid min-w-0 flex-1 grid-cols-[auto_1fr_1fr] items-start gap-2">
        <span className="mt-2 rounded-md bg-muted px-2 py-1 font-mono text-xs text-muted-foreground">
          phone
        </span>
        <TextInput
          name={`request_identifiers.${index}.param`}
          control={control}
          placeholder="Param name (e.g. phone)"
          className="font-mono text-[13px]"
        />
        <SelectInput
          name={`request_identifiers.${index}.in`}
          control={control}
          options={REQUEST_IDENTIFIER_IN_OPTIONS}
        />
      </div>
      {removable && (
        <CustomButton
          type="text"
          size="icon-xs"
          onClick={onRemove}
          className="mt-1 text-muted-foreground hover:text-destructive"
          aria-label="Remove identifier"
        >
          <Trash2 size={13} />
        </CustomButton>
      )}
    </div>
  );
}
