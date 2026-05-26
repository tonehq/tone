'use client';

import { useEffect, useMemo, useState } from 'react';

import {
  CheckboxField,
  CustomButton,
  CustomDrawer,
  RadioGroupField,
  SelectInput,
  TextAreaField,
  TextInput,
} from '@/components/shared';
import { listProviderCatalog, listProviderKeys } from '@/services/servicesService';
import type {
  ProviderCatalogItem,
  Service,
  ServiceKind,
  ServiceUpsertPayload,
} from '@/types/service';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';

interface ApiKeyCreateDrawerProps {
  open: boolean;
  /** Locks the provider Select to this id (used from the detail page). */
  lockedProviderId?: string | null;
  /** Pre-selected service_type when opening from a known context. */
  defaultServiceType?: ServiceKind | null;
  onClose: () => void;
  onSubmit: (payload: ServiceUpsertPayload) => Promise<void>;
  isPending: boolean;
}

const SERVICE_TYPE_OPTIONS = [
  { value: 'llm', label: 'LLM' },
  { value: 'stt', label: 'Speech-to-Text' },
  { value: 'tts', label: 'Text-to-Speech' },
];

const SERVICE_TYPE_LABEL: Record<ServiceKind, string> = {
  llm: 'LLM',
  stt: 'STT',
  tts: 'TTS',
};

const KEY_SOURCE_OPTIONS = [
  { value: 'new', label: 'Enter a new key' },
  { value: 'reuse', label: 'Use an existing key' },
];

type KeySource = 'new' | 'reuse';

interface FormState {
  service_type: ServiceKind | '';
  provider_id: string;
  label: string;
  description: string;
  is_default: boolean;
  is_active: boolean;
  api_key: string;
}

function initialFormState(
  lockedProviderId: string | null | undefined,
  defaultServiceType: ServiceKind | null | undefined,
): FormState {
  return {
    service_type: defaultServiceType ?? '',
    provider_id: lockedProviderId ?? '',
    label: '',
    description: '',
    is_default: false,
    is_active: true,
    api_key: '',
  };
}

export default function ApiKeyCreateDrawer({
  open,
  lockedProviderId,
  defaultServiceType,
  onClose,
  onSubmit,
  isPending,
}: ApiKeyCreateDrawerProps) {
  const [form, setForm] = useState<FormState>(() =>
    initialFormState(lockedProviderId, defaultServiceType),
  );
  const [providers, setProviders] = useState<ProviderCatalogItem[]>([]);
  const [catalogLoading, setCatalogLoading] = useState(false);

  // Existing keys for the currently selected provider — drives the
  // "Use an existing key" option so the user doesn't have to retype a
  // credential they've already stored (e.g. Deepgram STT → TTS).
  const [existingKeys, setExistingKeys] = useState<Service[]>([]);
  const [existingKeysLoading, setExistingKeysLoading] = useState(false);
  const [keySource, setKeySource] = useState<KeySource>('new');
  const [sourceKeyId, setSourceKeyId] = useState('');

  useEffect(() => {
    if (open) {
      setForm(initialFormState(lockedProviderId, defaultServiceType));
      setKeySource('new');
      setSourceKeyId('');
      setExistingKeys([]);
    }
  }, [open, lockedProviderId, defaultServiceType]);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setCatalogLoading(true);
    listProviderCatalog()
      .then((items) => {
        if (!cancelled) setProviders(items);
      })
      .catch((err) => {
        if (!cancelled) handleApiError(err);
      })
      .finally(() => {
        if (!cancelled) setCatalogLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open]);

  // Fetch existing keys whenever the selected provider changes. Skip when the
  // drawer is closed or no provider has been picked yet.
  useEffect(() => {
    // Reset selection when the provider changes so we don't carry a key id
    // that belongs to the previous provider into the new options.
    setSourceKeyId('');
    if (!open || !form.provider_id) {
      setExistingKeys([]);
      return;
    }
    let cancelled = false;
    setExistingKeysLoading(true);
    listProviderKeys(form.provider_id, { page: 1, page_size: 100, status: 'active' })
      .then((res) => {
        if (cancelled) return;
        setExistingKeys(res.rows);
      })
      .catch((err) => {
        if (!cancelled) handleApiError(err);
      })
      .finally(() => {
        if (!cancelled) setExistingKeysLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, form.provider_id]);

  // When existing keys arrive, pre-select the default (or first) so the
  // "reuse" option works on first click without an extra interaction.
  useEffect(() => {
    if (existingKeys.length === 0) {
      setSourceKeyId('');
      if (keySource === 'reuse') setKeySource('new');
      return;
    }
    const preferred = existingKeys.find((k) => k.is_default) ?? existingKeys[0];
    setSourceKeyId((prev) => prev || preferred.id);
  }, [existingKeys, keySource]);

  const providerOptions = useMemo(() => {
    const filtered = form.service_type
      ? providers.filter((p) => p.kinds.includes(form.service_type as ServiceKind))
      : providers;
    return filtered.map((p) => ({ value: p.id, label: p.display_name }));
  }, [providers, form.service_type]);

  const existingKeyOptions = useMemo(
    () =>
      existingKeys.map((k) => ({
        value: k.id,
        label: `${k.label || 'Unnamed key'} · ${SERVICE_TYPE_LABEL[k.service_type]}`,
      })),
    [existingKeys],
  );

  const update = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleServiceTypeChange = (value: string) => {
    update('service_type', value as ServiceKind);
    if (lockedProviderId) return;
    if (form.provider_id) {
      const p = providers.find((pp) => pp.id === form.provider_id);
      if (p && !p.kinds.includes(value as ServiceKind)) {
        update('provider_id', '');
      }
    }
  };

  const trimmedKey = form.api_key.trim();
  const canSubmit =
    form.service_type !== '' &&
    form.provider_id !== '' &&
    (keySource === 'new' ? trimmedKey.length > 0 : sourceKeyId !== '');

  const handleConfirm = async () => {
    if (!canSubmit) {
      showToast.error(
        'Required fields missing',
        keySource === 'reuse'
          ? 'Provider, service type, and an existing key are required.'
          : 'Provider, service type, and key are required.',
      );
      return;
    }

    const payload: ServiceUpsertPayload = {
      provider_id: form.provider_id,
      service_type: form.service_type as ServiceKind,
      label: form.label.trim() || undefined,
      description: form.description.trim() || undefined,
      is_default: form.is_default,
      is_active: form.is_active,
      ...(keySource === 'new' ? { api_key: trimmedKey } : { source_key_id: sourceKeyId }),
    };

    try {
      await onSubmit(payload);
    } catch (err) {
      handleApiError(err);
    }
  };

  const providerDisabled = !!lockedProviderId || !form.service_type || providerOptions.length === 0;
  const providerPlaceholder = lockedProviderId
    ? ''
    : !form.service_type
      ? 'Pick a service type first'
      : providerOptions.length === 0
        ? 'No providers support this type'
        : 'Select a provider';

  const showKeySourceToggle = form.provider_id !== '' && existingKeys.length > 0;

  // When the drawer is opened from the listing page the user is adding a new
  // provider connection; from the detail page they're adding another key to
  // an already-connected provider, so the copy differs.
  const isAddingProvider = !lockedProviderId;
  const drawerTitle = isAddingProvider ? 'Add provider' : 'Add API key';
  const drawerDescription = isAddingProvider
    ? 'Connect a model provider with an API key so your agents can use it.'
    : 'Add another API key for this provider.';

  return (
    <CustomDrawer
      open={open}
      onClose={onClose}
      title={drawerTitle}
      description={drawerDescription}
      width="sm:max-w-lg"
      footer={
        <div className="flex justify-end gap-2">
          <CustomButton type="default" onClick={onClose} disabled={isPending}>
            Cancel
          </CustomButton>
          <CustomButton
            type="primary"
            onClick={handleConfirm}
            loading={isPending}
            disabled={!canSubmit}
          >
            Create
          </CustomButton>
        </div>
      }
    >
      <div className="flex flex-col gap-4 pt-1">
        <SelectInput
          name="service_type"
          label="Service type"
          options={SERVICE_TYPE_OPTIONS}
          value={form.service_type}
          onValueChange={handleServiceTypeChange}
          placeholder="Select a type"
          isRequired
        />
        <SelectInput
          name="provider_id"
          label="Provider"
          options={providerOptions}
          value={form.provider_id}
          onValueChange={(v) => update('provider_id', v)}
          placeholder={providerPlaceholder}
          loading={catalogLoading}
          disabled={providerDisabled}
          isRequired
        />
        <TextInput
          name="label"
          label="Service name"
          value={form.label}
          onChange={(e) => update('label', e.target.value)}
          placeholder="e.g. OpenAI production"
        />
        <TextAreaField
          id="description"
          label="Description"
          value={form.description}
          onChange={(e) => update('description', e.target.value)}
          rows={2}
          placeholder="Optional notes for your team."
        />
        {showKeySourceToggle && (
          <RadioGroupField
            name="key_source"
            label="API key"
            options={KEY_SOURCE_OPTIONS}
            value={keySource}
            onValueChange={(v) => setKeySource(v as KeySource)}
            orientation="horizontal"
          />
        )}
        {keySource === 'reuse' && showKeySourceToggle ? (
          <SelectInput
            name="source_key_id"
            label="Existing key"
            options={existingKeyOptions}
            value={sourceKeyId}
            onValueChange={setSourceKeyId}
            placeholder="Select an existing key"
            loading={existingKeysLoading}
            isRequired
          />
        ) : (
          <TextInput
            name="api_key"
            label={showKeySourceToggle ? 'New API key' : 'API key'}
            type="password"
            value={form.api_key}
            onChange={(e) => update('api_key', e.target.value)}
            placeholder="sk-..."
            isRequired
          />
        )}
        <div className="flex flex-wrap items-center gap-6">
          <CheckboxField
            id="is_active"
            label="Active"
            checked={form.is_active}
            onCheckedChange={(v) => update('is_active', !!v)}
          />
          <CheckboxField
            id="is_default"
            label="Default for this service type"
            checked={form.is_default}
            onCheckedChange={(v) => update('is_default', !!v)}
          />
        </div>
      </div>
    </CustomDrawer>
  );
}
