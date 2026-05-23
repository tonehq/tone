'use client';

import { useEffect, useMemo, useState } from 'react';

import {
  CheckboxField,
  CustomButton,
  CustomDrawer,
  SelectInput,
  TextAreaField,
  TextInput,
} from '@/components/shared';
import { listProviderCatalog } from '@/services/servicesService';
import type { ProviderCatalogItem, ServiceKind, ServiceUpsertPayload } from '@/types/service';
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

  useEffect(() => {
    if (open) {
      setForm(initialFormState(lockedProviderId, defaultServiceType));
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

  const providerOptions = useMemo(() => {
    const filtered = form.service_type
      ? providers.filter((p) => p.kinds.includes(form.service_type as ServiceKind))
      : providers;
    return filtered.map((p) => ({ value: p.id, label: p.display_name }));
  }, [providers, form.service_type]);

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
  const canSubmit = form.service_type !== '' && form.provider_id !== '' && trimmedKey.length > 0;

  const handleConfirm = async () => {
    if (!canSubmit) {
      showToast.error('Required fields missing', 'Provider, service type, and key are required.');
      return;
    }

    const payload: ServiceUpsertPayload = {
      provider_id: form.provider_id,
      service_type: form.service_type as ServiceKind,
      label: form.label.trim() || undefined,
      description: form.description.trim() || undefined,
      is_default: form.is_default,
      is_active: form.is_active,
      api_key: trimmedKey,
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

  return (
    <CustomDrawer
      open={open}
      onClose={onClose}
      title="Add API key"
      description="Connect a provider with an API key so your agents can use it."
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
        <TextInput
          name="api_key"
          label="API key"
          type="password"
          value={form.api_key}
          onChange={(e) => update('api_key', e.target.value)}
          placeholder="sk-..."
          isRequired
        />
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
