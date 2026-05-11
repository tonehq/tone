'use client';

import {
  CheckboxField,
  CustomModal,
  SelectInput,
  TextAreaField,
  TextInput,
} from '@/components/shared';
import { type ProviderUpsertFormData, providerUpsertSchema } from '@/schemas/provider';
import { getApiKeyPlaintext } from '@/services/providerService';
import type { ServiceProvider, ServiceProviderUpsertPayload } from '@/types/provider';
import { handleApiError } from '@/utils/helpers';
import { zodResolver } from '@hookform/resolvers/zod';
import { Key } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';

const PROVIDER_TYPE_OPTIONS = [
  { value: 'llm', label: 'LLM' },
  { value: 'stt', label: 'STT' },
  { value: 'tts', label: 'TTS' },
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

  const { control, handleSubmit, reset, formState } = useForm<ProviderUpsertFormData>({
    resolver: zodResolver(providerUpsertSchema),
    defaultValues: { name: '', display_name: '', description: '', base_url: '' },
  });

  // Fields not in the zod schema (selects, checkboxes, api key section)
  const [providerType, setProviderType] = useState('llm');
  const [supportsStreaming, setSupportsStreaming] = useState(false);
  const [status, setStatus] = useState('active');

  const [apiKeyName, setApiKeyName] = useState('');
  const [apiKeyValue, setApiKeyValue] = useState('');
  const [originalApiKey, setOriginalApiKey] = useState('');
  const [apiKeyDescription, setApiKeyDescription] = useState('');
  const [apiKeyStatus, setApiKeyStatus] = useState('active');
  const [loadingKey, setLoadingKey] = useState(false);

  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    if (provider) {
      reset({
        name: provider.name,
        display_name: provider.display_name,
        description: provider.description ?? '',
        base_url: provider.base_url ?? '',
      });
      setProviderType(provider.provider_type);
      setSupportsStreaming(provider.supports_streaming ?? false);
      setStatus(provider.status ?? 'active');
      setApiKeyName(provider.api_key?.name ?? '');
      setApiKeyDescription(provider.api_key?.description ?? '');
      setApiKeyStatus(provider.api_key?.status ?? 'active');
      if (provider.api_key?.id) {
        setLoadingKey(true);
        setApiKeyValue('');
        setOriginalApiKey('');
        getApiKeyPlaintext(provider.api_key.id)
          .then((detail) => {
            setApiKeyValue(detail.api_key);
            setOriginalApiKey(detail.api_key);
          })
          .catch(handleApiError)
          .finally(() => setLoadingKey(false));
      } else {
        setApiKeyValue('');
        setOriginalApiKey('');
      }
    } else {
      reset({ name: '', display_name: '', description: '', base_url: '' });
      setProviderType('llm');
      setSupportsStreaming(false);
      setStatus('active');
      setApiKeyName('');
      setApiKeyValue('');
      setOriginalApiKey('');
      setApiKeyDescription('');
      setApiKeyStatus('active');
    }
  }, [open, provider, reset]);

  const onFormSubmit = useCallback(
    async (data: ProviderUpsertFormData) => {
      if (!isEdit && !apiKeyValue.trim()) return;
      setSaving(true);
      try {
        const trimmedKey = apiKeyValue.trim();
        const sendSecret = !isEdit ? !!trimmedKey : trimmedKey !== originalApiKey;
        const payload: ServiceProviderUpsertPayload = {
          name: data.name.trim(),
          display_name: data.display_name.trim(),
          provider_type: providerType as 'llm' | 'stt' | 'tts',
          auth_type: 'api_key',
          description: data.description?.trim() || undefined,
          base_url: data.base_url?.trim() || undefined,
          supports_streaming: supportsStreaming,
          status,
          api_key: {
            name: apiKeyName.trim() || `${data.display_name.trim()} key`,
            description: apiKeyDescription.trim() || undefined,
            status: apiKeyStatus,
            ...(sendSecret && trimmedKey ? { api_key: trimmedKey } : {}),
            ...(isEdit && provider?.api_key?.id ? { id: provider.api_key.id } : {}),
          },
        };
        if (isEdit) payload.id = provider.id;
        await onSubmit(payload);
        onClose();
      } finally {
        setSaving(false);
      }
    },
    [
      apiKeyValue,
      originalApiKey,
      providerType,
      supportsStreaming,
      status,
      apiKeyName,
      apiKeyDescription,
      apiKeyStatus,
      isEdit,
      provider,
      onSubmit,
      onClose,
    ],
  );

  const isApiKeyValid = isEdit || apiKeyValue.trim().length > 0;

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
      onConfirm={handleSubmit(onFormSubmit)}
      confirmLoading={saving}
      confirmDisabled={!formState.isValid || !isApiKeyValid}
      width="sm:max-w-xl"
      className={MODAL_CLASS}
      contentClassName={`pt-2 pb-2 max-h-[70vh] overflow-y-auto ${LABEL_COMPACT}`}
    >
      <div className="grid grid-cols-2 gap-x-3 gap-y-2.5">
        <TextInput
          name="name"
          control={control}
          label="Name"
          placeholder="e.g. openai"
          isRequired
        />
        <TextInput
          name="display_name"
          control={control}
          label="Display Name"
          placeholder="e.g. OpenAI"
          isRequired
        />

        <div className="col-span-2">
          <SelectInput
            name="provider-type"
            label="Provider Type"
            options={PROVIDER_TYPE_OPTIONS}
            value={providerType}
            onValueChange={setProviderType}
            isRequired
          />
        </div>

        <div className="col-span-2">
          <TextAreaField
            name="description"
            control={control}
            label="Description"
            placeholder="Describe this provider..."
            rows={2}
          />
        </div>

        <div className="col-span-2">
          <TextInput
            name="base_url"
            control={control}
            label="Base URL"
            placeholder="https://api.example.com"
          />
        </div>

        <SelectInput
          name="provider-status"
          label="Status"
          options={STATUS_OPTIONS}
          value={status}
          onValueChange={setStatus}
        />
        <div className="flex h-full flex-col justify-end">
          <div className="flex h-9 items-center rounded-md border border-input bg-background px-3">
            <CheckboxField
              id="supports-streaming"
              label="Supports Streaming"
              checked={supportsStreaming}
              onCheckedChange={(checked) => setSupportsStreaming(!!checked)}
              labelClassName="mt-1"
            />
          </div>
        </div>

        <div className="col-span-2 mt-1 border-t border-border pt-3">
          <div className="mb-2.5 flex items-center gap-1.5">
            <Key className="size-3.5 text-muted-foreground" />
            <span className="text-xs font-semibold text-foreground">API Key</span>
            {isEdit && provider?.api_key?.api_key_hint && (
              <span className="ml-auto font-mono text-[10px] text-muted-foreground">
                {provider.api_key.api_key_hint}
              </span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-x-3 gap-y-2.5">
            <TextInput
              name="api-key-name"
              label="Key Name"
              placeholder={`${formState.defaultValues?.display_name || 'Provider'} key`}
              value={apiKeyName}
              onChange={(e) => setApiKeyName(e.target.value)}
            />
            <TextInput
              name="api-key-value"
              label="API Key"
              placeholder={loadingKey ? 'Loading...' : 'sk-...'}
              type="password"
              value={apiKeyValue}
              onChange={(e) => setApiKeyValue(e.target.value)}
              isRequired={!isEdit}
              disabled={loadingKey}
            />
            <TextInput
              name="api-key-description"
              label="Key Description"
              placeholder="e.g. production credential"
              value={apiKeyDescription}
              onChange={(e) => setApiKeyDescription(e.target.value)}
            />
            <SelectInput
              name="api-key-status"
              label="Key Status"
              options={STATUS_OPTIONS}
              value={apiKeyStatus}
              onValueChange={setApiKeyStatus}
            />
          </div>
        </div>
      </div>
    </CustomModal>
  );
}
