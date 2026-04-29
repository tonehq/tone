'use client';

import {
  CheckboxField,
  CustomModal,
  SelectInput,
  TextAreaField,
  TextInput,
} from '@/components/shared';
import type { ServiceProvider, ServiceProviderUpsertPayload } from '@/types/provider';
import { useCallback, useEffect, useState } from 'react';

const PROVIDER_TYPE_OPTIONS = [
  { value: 'llm', label: 'LLM' },
  { value: 'stt', label: 'STT' },
  { value: 'tts', label: 'TTS' },
];

const AUTH_TYPE_OPTIONS = [
  { value: 'api_key', label: 'API Key' },
  { value: 'oauth', label: 'OAuth' },
  { value: 'none', label: 'None' },
];

const STATUS_OPTIONS = [
  { value: 'active', label: 'Active' },
  { value: 'inactive', label: 'Inactive' },
];

interface ProviderUpsertModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (payload: ServiceProviderUpsertPayload) => Promise<void>;
  provider?: ServiceProvider | null;
}

const MODAL_CLASS =
  '[&>div:first-child]:pt-3 [&>div:first-child]:pb-1 [&_[data-slot=dialog-description]]:mt-0.5';
const LABEL_COMPACT = '[&_label]:mb-1 [&_label]:text-xs';

export default function ProviderUpsertModal({
  open,
  onClose,
  onSubmit,
  provider,
}: ProviderUpsertModalProps) {
  const isEdit = !!provider;

  const [name, setName] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [providerType, setProviderType] = useState('llm');
  const [authType, setAuthType] = useState('api_key');
  const [description, setDescription] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [supportsStreaming, setSupportsStreaming] = useState(false);
  const [status, setStatus] = useState('active');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      if (provider) {
        setName(provider.name);
        setDisplayName(provider.display_name);
        setProviderType(provider.provider_type);
        setAuthType(provider.auth_type ?? 'api_key');
        setDescription(provider.description ?? '');
        setBaseUrl(provider.base_url ?? '');
        setSupportsStreaming(provider.supports_streaming ?? false);
        setStatus(provider.status ?? 'active');
      } else {
        setName('');
        setDisplayName('');
        setProviderType('llm');
        setAuthType('api_key');
        setDescription('');
        setBaseUrl('');
        setSupportsStreaming(false);
        setStatus('active');
      }
    }
  }, [open, provider]);

  const handleSubmit = useCallback(async () => {
    if (!name.trim() || !displayName.trim()) return;
    setSaving(true);
    try {
      const payload: ServiceProviderUpsertPayload = {
        name: name.trim(),
        display_name: displayName.trim(),
        provider_type: providerType as 'llm' | 'stt' | 'tts',
        auth_type: authType,
        description: description.trim() || undefined,
        base_url: baseUrl.trim() || undefined,
        supports_streaming: supportsStreaming,
        status,
      };
      if (isEdit) payload.id = provider.id;
      await onSubmit(payload);
      onClose();
    } finally {
      setSaving(false);
    }
  }, [
    name,
    displayName,
    providerType,
    authType,
    description,
    baseUrl,
    supportsStreaming,
    status,
    isEdit,
    provider,
    onSubmit,
    onClose,
  ]);

  const isValid = name.trim().length > 0 && displayName.trim().length > 0;

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Edit Service Provider' : 'Add Service Provider'}
      description={
        isEdit
          ? 'Update the service provider configuration.'
          : 'Add a new LLM, STT, or TTS service provider.'
      }
      confirmText={isEdit ? 'Save Changes' : 'Create Provider'}
      onConfirm={handleSubmit}
      confirmLoading={saving}
      confirmDisabled={!isValid}
      width="sm:max-w-xl"
      className={MODAL_CLASS}
      contentClassName={`pt-2 pb-3 ${LABEL_COMPACT}`}
    >
      <div className="flex flex-col gap-2.5">
        <div className="grid grid-cols-2 gap-3">
          <TextInput
            name="provider-name"
            label="Name"
            placeholder="e.g. openai"
            value={name}
            onChange={(e) => setName(e.target.value)}
            isRequired
          />
          <TextInput
            name="provider-display-name"
            label="Display Name"
            placeholder="e.g. OpenAI"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            isRequired
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <SelectInput
            name="provider-type"
            label="Provider Type"
            options={PROVIDER_TYPE_OPTIONS}
            value={providerType}
            onValueChange={setProviderType}
            isRequired
          />
          <SelectInput
            name="auth-type"
            label="Auth Type"
            options={AUTH_TYPE_OPTIONS}
            value={authType}
            onValueChange={setAuthType}
            isRequired
          />
        </div>

        <TextAreaField
          name="provider-description"
          label="Description"
          placeholder="Describe this provider..."
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={2}
        />

        <div className="grid grid-cols-2 gap-3">
          <TextInput
            name="provider-base-url"
            label="Base URL"
            placeholder="https://api.example.com"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
          />
          <SelectInput
            name="provider-status"
            label="Status"
            options={STATUS_OPTIONS}
            value={status}
            onValueChange={setStatus}
          />
        </div>

        <div className="mt-0.5">
          <CheckboxField
            id="supports-streaming"
            label="Supports Streaming"
            checked={supportsStreaming}
            onCheckedChange={(checked) => setSupportsStreaming(!!checked)}
          />
        </div>
      </div>
    </CustomModal>
  );
}
