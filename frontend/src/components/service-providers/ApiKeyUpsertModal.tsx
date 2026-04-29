'use client';

import { CustomModal, SelectInput, TextInput } from '@/components/shared';
import { getApiKeyPlaintext, upsertApiKey, type ApiKeyListRow } from '@/services/providerService';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { useCallback, useEffect, useState } from 'react';

const STATUS_OPTIONS = [
  { value: 'active', label: 'Active' },
  { value: 'inactive', label: 'Inactive' },
];

interface ApiKeyUpsertModalProps {
  open: boolean;
  onClose: () => void;
  onSaved: () => void | Promise<void>;
  serviceProviderId: number;
  apiKey?: ApiKeyListRow | null;
}

export default function ApiKeyUpsertModal({
  open,
  onClose,
  onSaved,
  serviceProviderId,
  apiKey,
}: ApiKeyUpsertModalProps) {
  const isEdit = !!apiKey;

  const [name, setName] = useState('');
  const [secret, setSecret] = useState('');
  const [originalSecret, setOriginalSecret] = useState('');
  const [description, setDescription] = useState('');
  const [status, setStatus] = useState('active');
  const [loadingKey, setLoadingKey] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    if (apiKey) {
      setName(apiKey.name ?? '');
      setDescription(apiKey.description ?? '');
      setStatus(apiKey.status ?? 'active');
      setLoadingKey(true);
      setSecret('');
      setOriginalSecret('');
      getApiKeyPlaintext(apiKey.id)
        .then((d) => {
          setSecret(d.api_key);
          setOriginalSecret(d.api_key);
        })
        .catch(handleApiError)
        .finally(() => setLoadingKey(false));
    } else {
      setName('');
      setSecret('');
      setOriginalSecret('');
      setDescription('');
      setStatus('active');
    }
  }, [open, apiKey]);

  const isValid = name.trim().length > 0 && (isEdit ? true : secret.trim().length > 0);

  const handleSubmit = useCallback(async () => {
    if (!isValid) return;
    const trimmed = secret.trim();
    if (
      isEdit &&
      trimmed === originalSecret &&
      name.trim() === (apiKey?.name ?? '') &&
      description.trim() === (apiKey?.description ?? '') &&
      status === (apiKey?.status ?? 'active')
    ) {
      onClose();
      return;
    }
    setSaving(true);
    try {
      // Backend always re-encrypts the secret on upsert; reuse existing secret if user didn't change it
      await upsertApiKey({
        service_provider_id: serviceProviderId,
        name: name.trim(),
        api_key: trimmed || originalSecret,
        description: description.trim() || undefined,
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
  }, [
    isValid,
    isEdit,
    name,
    secret,
    originalSecret,
    description,
    status,
    serviceProviderId,
    apiKey,
    onSaved,
    onClose,
  ]);

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
      onConfirm={handleSubmit}
      confirmLoading={saving}
      confirmDisabled={!isValid}
      width="sm:max-w-md"
    >
      <div className="grid gap-3">
        <TextInput
          name="api-key-name"
          label="Name"
          placeholder="e.g. Production"
          value={name}
          onChange={(e) => setName(e.target.value)}
          isRequired
        />
        <TextInput
          name="api-key-value"
          label="API Key"
          placeholder={loadingKey ? 'Loading...' : 'sk-...'}
          type="password"
          value={secret}
          onChange={(e) => setSecret(e.target.value)}
          disabled={loadingKey}
          isRequired={!isEdit}
        />
        <TextInput
          name="api-key-description"
          label="Description"
          placeholder="Optional"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
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
