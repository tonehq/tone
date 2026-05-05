'use client';

import {
  CheckboxField,
  CustomModal,
  SelectInput,
  TextAreaField,
  TextInput,
} from '@/components/shared';
import {
  listApiKeysByProvider,
  listServiceProviders,
  type ApiKeyListRow,
} from '@/services/providerService';
import type { Service, ServiceProvider, ServiceUpsertPayload } from '@/types/provider';
import { handleApiError } from '@/utils/helpers';
import { Key } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';

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

  // Provider list for dropdown
  const [providers, setProviders] = useState<ServiceProvider[]>([]);
  const [providersLoading, setProvidersLoading] = useState(false);

  // Form state
  const [selectedProviderId, setSelectedProviderId] = useState('');
  const [name, setName] = useState('');
  const [serviceType, setServiceType] = useState<string>('llm');
  const [description, setDescription] = useState('');
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

  // Load all providers on open
  useEffect(() => {
    if (!open) return;
    setProvidersLoading(true);
    listServiceProviders({ page_size: 0 })
      .then((result) => setProviders(result.providers))
      .catch(handleApiError)
      .finally(() => setProvidersLoading(false));
  }, [open]);

  // Provider dropdown options
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

  // Load API keys when provider changes
  useEffect(() => {
    const pid = Number(selectedProviderId);
    if (!pid) {
      setApiKeys([]);
      return;
    }
    listApiKeysByProvider({ service_provider_id: pid, page: 1, page_size: 100 })
      .then((result) => {
        setApiKeys(result.keys);
        if (!isEdit && result.keys.length > 0) {
          setSelectedApiKeyId(String(result.keys[0].id));
        }
      })
      .catch(handleApiError);
  }, [selectedProviderId, isEdit]);

  // Reset provider when service type changes (filtered list changes)
  const handleServiceTypeChange = useCallback(
    (val: string) => {
      setServiceType(val);
      if (!isEdit) {
        setSelectedProviderId('');
        setName('');
        setApiKeys([]);
      }
    },
    [isEdit],
  );

  // Auto-set name when provider changes
  const handleProviderChange = useCallback(
    (val: string) => {
      setSelectedProviderId(val);
      const provider = providers.find((p) => p.id === Number(val));
      if (provider && !isEdit) {
        setName(`${provider.display_name} ${serviceType.toUpperCase()}`);
      }
    },
    [providers, isEdit, serviceType],
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

  // Populate form on open
  useEffect(() => {
    if (!open) return;
    if (service) {
      setSelectedProviderId(String(service.service_provider_id));
      setName(service.name);
      setServiceType(service.service_type ?? 'llm');
      setDescription(service.description ?? '');
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
      setSelectedProviderId('');
      setName('');
      setServiceType('llm');
      setDescription('');
      setStatus('active');
      setIsDefault(false);
      setSelectedApiKeyId('');
      setNewApiKeyValue('');
      setNewApiKeyName('');
      setConfigStr('{}');
      setApiKeys([]);
    }
    setConfigError('');
  }, [open, service]);

  const handleSubmit = useCallback(async () => {
    if (!name.trim() || !selectedProviderId) return;

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
        service_provider_id: Number(selectedProviderId),
        name: name.trim(),
        service_type: serviceType,
        config,
        description: description.trim() || undefined,
        status,
        is_default: isDefault,
        ...(isEdit && service?.uuid ? { uuid: service.uuid } : {}),
        ...(isNewKey
          ? {
              api_key_value: newApiKeyValue.trim(),
              api_key_name: newApiKeyName.trim() || `${name.trim()} key`,
            }
          : { api_key_id: Number(selectedApiKeyId) || null }),
      };
      await onSubmit(payload);
      onClose();
    } finally {
      setSaving(false);
    }
  }, [
    name,
    selectedProviderId,
    serviceType,
    description,
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
  ]);

  const isNewKey = selectedApiKeyId === '__new__';
  const hasApiKey = isNewKey ? newApiKeyValue.trim().length > 0 : !!selectedApiKeyId;
  const isValid = name.trim().length > 0 && !!selectedProviderId && hasApiKey;

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
      onConfirm={handleSubmit}
      confirmLoading={saving}
      confirmDisabled={!isValid}
      width="sm:max-w-xl"
      className={MODAL_CLASS}
      contentClassName={`pt-2 pb-2 max-h-[70vh] overflow-y-auto ${LABEL_COMPACT}`}
    >
      <div className="grid grid-cols-2 gap-x-3 gap-y-2.5">
        {/* Service Type first */}
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

        {/* Provider dropdown */}
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

        <div className="col-span-2">
          <TextInput
            name="service-name"
            label="Service Name"
            placeholder="e.g. OpenAI LLM"
            value={name}
            onChange={(e) => setName(e.target.value)}
            isRequired
          />
        </div>

        <div className="col-span-2">
          <TextAreaField
            name="service-description"
            label="Description"
            placeholder="Describe this service..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
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

        {/* ── API Key ──────────────────────────────────────────────── */}
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

        {/* ── Config ───────────────────────────────────────────────── */}
        <div className="col-span-2 mt-1 border-t border-border pt-3">
          <label
            htmlFor="service-config"
            className="mb-1 block text-xs font-medium text-foreground"
          >
            Config (JSON)
          </label>
          <textarea
            id="service-config"
            value={configStr}
            onChange={(e) => {
              setConfigStr(e.target.value);
              if (configError) setConfigError('');
            }}
            placeholder="{}"
            rows={3}
            className="w-full resize-none rounded-md border border-input bg-background px-3 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground focus-visible:border-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30"
          />
          {configError && <p className="mt-1 text-xs text-destructive">{configError}</p>}
        </div>
      </div>
    </CustomModal>
  );
}
