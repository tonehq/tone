'use client';

import {
  CheckboxField,
  CustomModal,
  SelectInput,
  TextAreaField,
  TextInput,
} from '@/components/shared';
import ProviderLogo from '@/components/service-providers/ProviderLogo';
import { type ServiceUpsertFormData, serviceUpsertSchema } from '@/schemas/provider';
import { listServiceProviders, type ApiKeyListRow } from '@/services/providerService';
import type { Service, ServiceProvider, ServiceUpsertPayload } from '@/types/provider';
import { handleApiError } from '@/utils/helpers';
import { zodResolver } from '@hookform/resolvers/zod';
import { Key } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';

const SERVICE_TYPE_OPTIONS = [
  { value: 'llm', label: 'LLM' },
  { value: 'stt', label: 'STT' },
  { value: 'tts', label: 'TTS' },
];

const STATUS_OPTIONS = [
  { value: 'active', label: 'Active' },
  { value: 'inactive', label: 'Inactive' },
];

interface ServiceUpsertModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (payload: ServiceUpsertPayload) => Promise<void>;
  service?: Service | null;
}

const MODAL_CLASS =
  '[&>div:first-child]:pt-3 [&>div:first-child]:pb-1 [&_[data-slot=dialog-description]]:mt-0.5';
const LABEL_COMPACT = '[&_label]:mb-1 [&_label]:text-xs';

export default function ServiceUpsertModal({
  open,
  onClose,
  onSubmit,
  service,
}: ServiceUpsertModalProps) {
  const isEdit = !!service;

  const { control, handleSubmit, reset, formState, setValue } = useForm<ServiceUpsertFormData>({
    resolver: zodResolver(serviceUpsertSchema),
    defaultValues: { name: '', description: '' },
  });

  // Provider list for dropdown
  const [providers, setProviders] = useState<ServiceProvider[]>([]);
  const [providersLoading, setProvidersLoading] = useState(false);

  // Non-zod form state
  const [selectedProviderId, setSelectedProviderId] = useState('');
  const [serviceType, setServiceType] = useState<string>('llm');
  const [status, setStatus] = useState('active');
  const [isDefault, setIsDefault] = useState(false);

  // API Keys for selected provider
  const [apiKeys, setApiKeys] = useState<ApiKeyListRow[]>([]);
  const [selectedApiKeyId, setSelectedApiKeyId] = useState('');
  const [newApiKeyValue, setNewApiKeyValue] = useState('');
  const [newApiKeyName, setNewApiKeyName] = useState('');

  const [configStr, setConfigStr] = useState('{}');
  const [configError, setConfigError] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setProvidersLoading(true);
    listServiceProviders({ page_size: 0 })
      .then((result) => setProviders(result.providers))
      .catch(handleApiError)
      .finally(() => setProvidersLoading(false));
  }, [open]);

  const providerOptions = useMemo(
    () =>
      providers
        .filter((p) => p.provider_type === serviceType)
        .map((p) => ({
          value: String(p.id),
          label: p.display_name,
        })),
    [providers, serviceType],
  );

  const selectedProvider = useMemo(
    () => providers.find((p) => p.id === Number(selectedProviderId)),
    [providers, selectedProviderId],
  );

  useEffect(() => {
    const pid = Number(selectedProviderId);
    if (!pid) {
      setApiKeys([]);
      return;
    }
    // In edit mode, show the existing key from the account
    if (isEdit && service?.api_key_id) {
      setApiKeys([
        {
          id: service.api_key_id,
          name: service.name,
          api_key_hint: service.api_key_hint ?? '',
        } as ApiKeyListRow,
      ]);
      setSelectedApiKeyId(String(service.api_key_id));
    } else {
      // For new accounts, default to creating a new key
      setApiKeys([]);
      setSelectedApiKeyId('__new__');
    }
  }, [selectedProviderId, isEdit, service]);

  const handleServiceTypeChange = useCallback(
    (val: string) => {
      setServiceType(val);
      if (!isEdit) {
        setSelectedProviderId('');
        setValue('name', '');
        setApiKeys([]);
      }
    },
    [isEdit, setValue],
  );

  const handleProviderChange = useCallback(
    (val: string) => {
      setSelectedProviderId(val);
      const provider = providers.find((p) => p.id === Number(val));
      if (provider && !isEdit) {
        setValue('name', `${provider.display_name} ${serviceType.toUpperCase()}`);
      }
    },
    [providers, isEdit, serviceType, setValue],
  );

  const apiKeyOptions = useMemo(
    () => [
      { value: '__new__', label: '+ Create new key' },
      ...apiKeys.map((k) => ({
        value: String(k.id),
        label: `${k.name} (${k.api_key_hint})`,
      })),
    ],
    [apiKeys],
  );

  useEffect(() => {
    if (!open) return;
    if (service) {
      reset({ name: service.name, description: service.description ?? '' });
      setSelectedProviderId(String(service.model_provider_menu_id));
      setServiceType(service.service_type ?? 'llm');
      setStatus(service.status ?? 'active');
      setIsDefault(service.is_default ?? false);
      setSelectedApiKeyId(service.api_key_id ? String(service.api_key_id) : '');
      setNewApiKeyValue('');
      setNewApiKeyName('');
      setConfigStr(
        service.config && Object.keys(service.config).length > 0
          ? JSON.stringify(service.config, null, 2)
          : '{}',
      );
    } else {
      reset({ name: '', description: '' });
      setSelectedProviderId('');
      setServiceType('llm');
      setStatus('active');
      setIsDefault(false);
      setSelectedApiKeyId('');
      setNewApiKeyValue('');
      setNewApiKeyName('');
      setConfigStr('{}');
      setApiKeys([]);
    }
    setConfigError('');
  }, [open, service, reset]);

  const onFormSubmit = useCallback(
    async (data: ServiceUpsertFormData) => {
      if (!selectedProviderId) return;

      let config: Record<string, unknown> = {};
      if (configStr.trim()) {
        try {
          config = JSON.parse(configStr.trim());
          setConfigError('');
        } catch {
          setConfigError('Invalid JSON format');
          return;
        }
      }

      const isNewKey = selectedApiKeyId === '__new__';
      if (isNewKey && !newApiKeyValue.trim()) return;

      setSaving(true);
      try {
        const payload: ServiceUpsertPayload = {
          model_provider_menu_id: Number(selectedProviderId),
          name: data.name.trim(),
          service_type: serviceType,
          config,
          description: data.description?.trim() || undefined,
          status,
          is_default: isDefault,
          ...(isEdit && service?.uuid ? { uuid: service.uuid } : {}),
          ...(isNewKey
            ? {
                api_key_value: newApiKeyValue.trim(),
                api_key_name: newApiKeyName.trim() || `${data.name.trim()} key`,
              }
            : { api_key_id: Number(selectedApiKeyId) || null }),
        };
        await onSubmit(payload);
        onClose();
      } finally {
        setSaving(false);
      }
    },
    [
      selectedProviderId,
      serviceType,
      status,
      isDefault,
      selectedApiKeyId,
      newApiKeyValue,
      newApiKeyName,
      configStr,
      isEdit,
      service,
      onSubmit,
      onClose,
    ],
  );

  const isNewKey = selectedApiKeyId === '__new__';
  const hasApiKey = isNewKey ? newApiKeyValue.trim().length > 0 : !!selectedApiKeyId;
  const isExtraValid = !!selectedProviderId && hasApiKey;

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Edit Service' : 'Add Service'}
      description={
        isEdit
          ? 'Update the service configuration.'
          : 'Create a new service by selecting a provider.'
      }
      confirmText={isEdit ? 'Save Changes' : 'Create Service'}
      onConfirm={handleSubmit(onFormSubmit)}
      confirmLoading={saving}
      confirmDisabled={!formState.isValid || !isExtraValid}
      width="sm:max-w-xl"
      className={MODAL_CLASS}
      contentClassName={`pt-2 pb-2 max-h-[70vh] overflow-y-auto ${LABEL_COMPACT}`}
    >
      <div className="grid grid-cols-2 gap-x-3 gap-y-2.5">
        <div className="col-span-2">
          <SelectInput
            name="service-type"
            label="Service Type"
            options={SERVICE_TYPE_OPTIONS}
            value={serviceType}
            onValueChange={handleServiceTypeChange}
            isRequired
          />
        </div>

        <div className="col-span-2">
          <SelectInput
            name="service-provider"
            label="Service Provider"
            placeholder="Select a provider..."
            options={providerOptions}
            value={selectedProviderId}
            onValueChange={handleProviderChange}
            loading={providersLoading}
            isRequired
            disabled={isEdit}
          />
        </div>

        {selectedProvider && (
          <div className="col-span-2 -mt-1 flex items-center gap-2.5 rounded-lg border border-border bg-muted/30 p-2.5">
            <ProviderLogo
              providerName={selectedProvider.name}
              serviceType={selectedProvider.provider_type}
              className="size-9 rounded-md"
              imgSize={20}
            />
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-foreground">
                {selectedProvider.display_name}
              </p>
              <p className="truncate font-mono text-[11px] text-muted-foreground">
                {selectedProvider.name}
              </p>
            </div>
          </div>
        )}

        <div className="col-span-2">
          <TextInput
            name="name"
            control={control}
            label="Service Name"
            placeholder="e.g. OpenAI LLM"
            isRequired
          />
        </div>

        <div className="col-span-2">
          <TextAreaField
            name="description"
            control={control}
            label="Description"
            placeholder="Describe this service..."
            rows={2}
          />
        </div>

        <SelectInput
          name="service-status"
          label="Status"
          options={STATUS_OPTIONS}
          value={status}
          onValueChange={setStatus}
        />
        <div className="flex h-full flex-col justify-end">
          <div className="flex h-9 items-center rounded-md border border-input bg-background px-3">
            <CheckboxField
              id="service-is-default"
              label="Default service"
              checked={isDefault}
              onCheckedChange={(checked) => setIsDefault(!!checked)}
            />
          </div>
        </div>

        {selectedProviderId && (
          <div className="col-span-2 mt-1 border-t border-border pt-3">
            <div className="mb-2.5 flex items-center gap-1.5">
              <Key className="size-3.5 text-muted-foreground" />
              <span className="text-xs font-semibold text-foreground">API Key</span>
            </div>
            <div className="grid grid-cols-2 gap-x-3 gap-y-2.5">
              <div className="col-span-2">
                <SelectInput
                  name="service-api-key"
                  label="Select API Key"
                  options={apiKeyOptions}
                  value={selectedApiKeyId}
                  onValueChange={setSelectedApiKeyId}
                  isRequired
                />
              </div>
              {isNewKey && (
                <>
                  <TextInput
                    name="new-api-key-name"
                    label="Key Name"
                    placeholder="My API key"
                    value={newApiKeyName}
                    onChange={(e) => setNewApiKeyName(e.target.value)}
                  />
                  <TextInput
                    name="new-api-key-value"
                    label="API Key"
                    placeholder="sk-..."
                    type="password"
                    value={newApiKeyValue}
                    onChange={(e) => setNewApiKeyValue(e.target.value)}
                    isRequired
                  />
                </>
              )}
            </div>
          </div>
        )}

        <div className="col-span-2 mt-1 border-t border-border pt-3">
          <TextAreaField
            name="service-config"
            label="Config (JSON)"
            placeholder="{}"
            value={configStr}
            onChange={(e) => {
              setConfigStr(e.target.value);
              if (configError) setConfigError('');
            }}
            rows={3}
            className="font-mono"
            error={!!configError}
            helperText={configError || undefined}
          />
        </div>
      </div>
    </CustomModal>
  );
}
