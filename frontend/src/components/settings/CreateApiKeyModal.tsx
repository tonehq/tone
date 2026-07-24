'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';

import { CustomModal, DateTimePicker, RadioGroupField, TextInput } from '@/components/shared';
import {
  EXPIRY_LABELS,
  type CreateApiKeyFormData,
  createApiKeySchema,
  expiryChoiceToIso,
  type ExpiryChoice,
} from '@/schemas/apiKey';
import type { CreateApiKeyPayload } from '@/types/settings/apiKey';
import { showToast } from '@/utils/toast';

interface CreateApiKeyModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (payload: CreateApiKeyPayload) => Promise<void>;
}

const EXPIRY_OPTIONS: { value: ExpiryChoice; label: string }[] = (
  ['7d', '30d', '60d', '90d', 'custom', 'never'] as const
).map((v) => ({ value: v, label: EXPIRY_LABELS[v] }));

export default function CreateApiKeyModal({ open, onClose, onSubmit }: CreateApiKeyModalProps) {
  const { control, handleSubmit, reset, watch, setValue, formState } =
    useForm<CreateApiKeyFormData>({
      resolver: zodResolver(createApiKeySchema),
      defaultValues: { name: '', expiry: '30d', customExpiresAt: null },
    });

  const [customTimeZone, setCustomTimeZone] = useState<string>(
    Intl.DateTimeFormat().resolvedOptions().timeZone,
  );
  const [saving, setSaving] = useState(false);
  const expiry = watch('expiry');
  const customExpiresAt = watch('customExpiresAt');

  useEffect(() => {
    if (open) {
      reset({ name: '', expiry: '30d', customExpiresAt: null });
    }
  }, [open, reset]);

  const onFormSubmit = async (data: CreateApiKeyFormData) => {
    // Local (client-side) validation of the custom-expiry picker runs first —
    // its errors surface here as a toast. API errors are toasted by the parent
    // via handleApiError, so we do NOT re-toast them (avoids a double toast).
    let expires_at: string | null;
    try {
      expires_at = expiryChoiceToIso(data.expiry, data.customExpiresAt ?? null);
    } catch (err) {
      if (err instanceof Error) showToast.error(err.message);
      return;
    }
    setSaving(true);
    try {
      await onSubmit({ name: data.name.trim(), expires_at });
      onClose();
    } catch {
      // Parent already surfaced the API error via handleApiError.
    } finally {
      setSaving(false);
    }
  };

  const confirmDisabled = !formState.isValid || (expiry === 'custom' && !customExpiresAt) || saving;

  return (
    <CustomModal
      open={open}
      onClose={saving ? () => undefined : onClose}
      title="Create API Key"
      description="Give the key a name and choose when it should expire. You'll see the full key once — copy it now."
      confirmText="Create key"
      onConfirm={handleSubmit(onFormSubmit)}
      confirmLoading={saving}
      confirmDisabled={confirmDisabled}
    >
      <div className="space-y-4">
        <TextInput
          name="name"
          control={control}
          label="Name"
          placeholder="e.g. Production, CI job, Local dev"
          isRequired
          disabled={saving}
        />
        <RadioGroupField
          name="expiry"
          label="Expires"
          options={EXPIRY_OPTIONS}
          value={expiry}
          onValueChange={(v) => setValue('expiry', v as ExpiryChoice, { shouldValidate: true })}
          orientation="horizontal"
          disabled={saving}
        />
        {expiry === 'custom' && (
          <DateTimePicker
            value={{ value: customExpiresAt ?? null, timeZone: customTimeZone }}
            onChange={(v) => {
              setValue('customExpiresAt', v.value, { shouldValidate: true });
              setCustomTimeZone(v.timeZone);
            }}
            placeholder="Pick an expiry date and time"
            disabled={saving}
          />
        )}
      </div>
    </CustomModal>
  );
}
