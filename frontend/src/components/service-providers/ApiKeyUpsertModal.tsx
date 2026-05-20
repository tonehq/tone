'use client';

import { CustomModal, SelectInput, TextInput } from '@/components/shared';
import {
  type ApiKeyCreateFormData,
  type ApiKeyUpsertFormData,
  apiKeyCreateSchema,
  apiKeyUpsertSchema,
} from '@/schemas/provider';
import { getApiKeyPlaintext, upsertApiKey, type ApiKeyListRow } from '@/services/providerService';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { zodResolver } from '@hookform/resolvers/zod';
import { useCallback, useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';

const STATUS_OPTIONS = [
  { value: 'active', label: 'Active' },
  { value: 'inactive', label: 'Inactive' },
];

interface ApiKeyUpsertModalProps {
  open: boolean;
  onClose: () => void;
  onSaved: () => void | Promise<void>;
  accountId: number;
  apiKey?: ApiKeyListRow | null;
}

export default function ApiKeyUpsertModal({
  open,
  onClose,
  onSaved,
  accountId,
  apiKey,
}: ApiKeyUpsertModalProps) {
  const isEdit = !!apiKey;

  const { control, handleSubmit, reset, formState } = useForm<
    ApiKeyUpsertFormData | ApiKeyCreateFormData
  >({
    resolver: zodResolver(isEdit ? apiKeyUpsertSchema : apiKeyCreateSchema),
    defaultValues: { name: '', api_key: '', description: '' },
  });

  const [originalSecret, setOriginalSecret] = useState('');
  const [status, setStatus] = useState('active');
  const [loadingKey, setLoadingKey] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    if (apiKey) {
      setStatus(apiKey.status ?? 'active');
      setLoadingKey(true);
      reset({ name: apiKey.name ?? '', api_key: '', description: apiKey.description ?? '' });
      setOriginalSecret('');
      getApiKeyPlaintext(apiKey.id)
        .then((d) => {
          reset({
            name: apiKey.name ?? '',
            api_key: d.api_key,
            description: apiKey.description ?? '',
          });
          setOriginalSecret(d.api_key);
        })
        .catch(handleApiError)
        .finally(() => setLoadingKey(false));
    } else {
      reset({ name: '', api_key: '', description: '' });
      setOriginalSecret('');
      setStatus('active');
    }
  }, [open, apiKey, reset]);

  const onFormSubmit = useCallback(
    async (data: ApiKeyUpsertFormData | ApiKeyCreateFormData) => {
      const trimmed = (data.api_key ?? '').trim();
      if (
        isEdit &&
        trimmed === originalSecret &&
        data.name.trim() === (apiKey?.name ?? '') &&
        (data.description ?? '').trim() === (apiKey?.description ?? '') &&
        status === (apiKey?.status ?? 'active')
      ) {
        onClose();
        return;
      }
      setSaving(true);
      try {
        await upsertApiKey({
          account_id: accountId,
          name: data.name.trim(),
          api_key: trimmed || originalSecret,
          description: data.description?.trim() || undefined,
          status,
          uuid: isEdit ? apiKey?.uuid : undefined,
        });
        showToast.success(isEdit ? 'API key updated' : 'API key added');
        await onSaved();
        onClose();
      } catch (error) {
        handleApiError(error);
      } finally {
        setSaving(false);
      }
    },
    [isEdit, originalSecret, status, accountId, apiKey, onSaved, onClose],
  );

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Edit API Key' : 'Add API Key'}
      description={
        isEdit
          ? 'Update the credential. Leaving the value unchanged keeps the existing secret.'
          : 'Add a new credential for this service provider.'
      }
      confirmText={isEdit ? 'Save Changes' : 'Add Key'}
      onConfirm={handleSubmit(onFormSubmit)}
      confirmLoading={saving}
      confirmDisabled={!formState.isValid}
      width="sm:max-w-md"
    >
      <div className="grid gap-3">
        <TextInput
          name="name"
          control={control}
          label="Name"
          placeholder="e.g. Production"
          isRequired
        />
        <TextInput
          name="api_key"
          control={control}
          label="API Key"
          placeholder={loadingKey ? 'Loading...' : 'sk-...'}
          type="password"
          disabled={loadingKey}
          isRequired
        />
        <TextInput
          name="description"
          control={control}
          label="Description"
          placeholder="Optional"
        />
        <SelectInput
          name="api-key-status"
          label="Status"
          options={STATUS_OPTIONS}
          value={status}
          onValueChange={setStatus}
        />
      </div>
    </CustomModal>
  );
}
