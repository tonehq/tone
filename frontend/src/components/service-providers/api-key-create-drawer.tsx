'use client';

import { Plus } from 'lucide-react';
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
  ModelProvider,
  ModelProviderUpsertPayload,
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
  /**
   * When provided, the drawer exposes a "Create new provider" toggle so the
   * user can define a brand-new ModelProvider inline instead of picking from
   * the catalog. The returned provider is used as the API key's ``provider_id``.
   * Omitted from the detail-page usage where the provider is locked.
   */
  onCreateProvider?: (payload: ModelProviderUpsertPayload) => Promise<ModelProvider>;
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
type ProviderMode = 'existing' | 'new';

interface FormState {
  service_type: ServiceKind | '';
  provider_id: string;
  label: string;
  description: string;
  is_default: boolean;
  is_active: boolean;
  api_key: string;
}

interface NewProviderState {
  display_name: string;
  provider_id: string;
  slug: string;
  description: string;
  website_url: string;
}

const EMPTY_NEW_PROVIDER: NewProviderState = {
  display_name: '',
  provider_id: '',
  slug: '',
  description: '',
  website_url: '',
};

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

// Lowercase, non-alphanumerics → single dash, trimmed. Used to auto-derive the
// short identifier and slug from the display name so admins don't have to
// hand-type both.
function slugify(input: string): string {
  return input
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

export default function ApiKeyCreateDrawer({
  open,
  lockedProviderId,
  defaultServiceType,
  onClose,
  onSubmit,
  onCreateProvider,
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

  // Inline "create new provider" mode. Only available when the caller supplied
  // ``onCreateProvider`` AND the drawer isn't locked to an existing provider.
  const [providerMode, setProviderMode] = useState<ProviderMode>('existing');
  const [newProvider, setNewProvider] = useState<NewProviderState>(EMPTY_NEW_PROVIDER);
  // Track manual edits so auto-slugging from display_name doesn't clobber
  // whatever the user has already typed into these fields themselves.
  const [newProviderTouched, setNewProviderTouched] = useState({
    provider_id: false,
    slug: false,
  });
  const [creatingProvider, setCreatingProvider] = useState(false);

  const canCreateProvider = !!onCreateProvider && !lockedProviderId;

  useEffect(() => {
    if (open) {
      setForm(initialFormState(lockedProviderId, defaultServiceType));
      setKeySource('new');
      setSourceKeyId('');
      setExistingKeys([]);
      setProviderMode('existing');
      setNewProvider(EMPTY_NEW_PROVIDER);
      setNewProviderTouched({ provider_id: false, slug: false });
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
  // drawer is closed, we're creating a brand-new provider, or no provider has
  // been picked yet.
  useEffect(() => {
    // Reset selection when the provider changes so we don't carry a key id
    // that belongs to the previous provider into the new options.
    setSourceKeyId('');
    if (!open || providerMode === 'new' || !form.provider_id) {
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
  }, [open, form.provider_id, providerMode]);

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
  const hasKey = trimmedKey.length > 0;

  const newProviderComplete =
    newProvider.display_name.trim().length > 0 &&
    newProvider.provider_id.trim().length > 0 &&
    newProvider.slug.trim().length > 0;

  // In "new provider" mode the API key is optional — a user may want to just
  // register the provider now and add credentials later. When a key IS given
  // the service_type becomes required so we know which ApiKey slot to fill.
  // In "existing" mode we always need a provider, a service type, and a key.
  const canSubmit =
    providerMode === 'new'
      ? newProviderComplete && (!hasKey || form.service_type !== '')
      : form.service_type !== '' &&
        form.provider_id !== '' &&
        (keySource === 'new' ? hasKey : sourceKeyId !== '');

  const updateNewProvider = <K extends keyof NewProviderState>(
    key: K,
    value: NewProviderState[K],
  ) => {
    setNewProvider((prev) => ({ ...prev, [key]: value }));
  };

  const handleNewProviderDisplayName = (value: string) => {
    setNewProvider((prev) => ({
      ...prev,
      display_name: value,
      provider_id: newProviderTouched.provider_id ? prev.provider_id : slugify(value),
      slug: newProviderTouched.slug ? prev.slug : slugify(value),
    }));
  };

  const handleEnterCreateProviderMode = () => {
    setProviderMode('new');
    update('provider_id', '');
    setKeySource('new');
    setSourceKeyId('');
  };

  const handleExitCreateProviderMode = () => {
    setProviderMode('existing');
    setNewProvider(EMPTY_NEW_PROVIDER);
    setNewProviderTouched({ provider_id: false, slug: false });
  };

  const handleConfirm = async () => {
    if (!canSubmit) {
      const detail =
        providerMode === 'new'
          ? hasKey
            ? 'Provider details and service type are required when an API key is set.'
            : 'Display name, identifier, and slug are required.'
          : keySource === 'reuse'
            ? 'Provider, service type, and an existing key are required.'
            : 'Provider, service type, and key are required.';
      showToast.error('Required fields missing', detail);
      return;
    }

    try {
      // "New provider" mode: create the ModelProvider first, then decide
      // whether to also create an ApiKey. Skipping the ApiKey lets admins
      // register a provider now and add credentials later.
      if (providerMode === 'new') {
        if (!onCreateProvider) return;
        setCreatingProvider(true);
        let created;
        try {
          created = await onCreateProvider({
            provider_id: newProvider.provider_id.trim(),
            slug: newProvider.slug.trim(),
            display_name: newProvider.display_name.trim(),
            description: newProvider.description.trim() || undefined,
            website_url: newProvider.website_url.trim() || undefined,
            is_active: true,
          });
        } finally {
          setCreatingProvider(false);
        }

        if (!hasKey) {
          // Provider-only creation — no ApiKey to POST, so we short-circuit
          // the parent's onSubmit path (which would otherwise 400 on the
          // missing key). Close the drawer here since we skip the parent's
          // close/refresh side effects.
          showToast.success(
            'Provider created',
            'You can add an API key for this provider anytime.',
          );
          onClose();
          return;
        }

        const payload: ServiceUpsertPayload = {
          provider_id: created.id,
          service_type: form.service_type as ServiceKind,
          label: form.label.trim() || undefined,
          description: form.description.trim() || undefined,
          is_default: form.is_default,
          is_active: form.is_active,
          api_key: trimmedKey,
        };
        await onSubmit(payload);
        return;
      }

      const payload: ServiceUpsertPayload = {
        provider_id: form.provider_id,
        service_type: form.service_type as ServiceKind,
        label: form.label.trim() || undefined,
        description: form.description.trim() || undefined,
        is_default: form.is_default,
        is_active: form.is_active,
        ...(keySource === 'reuse' ? { source_key_id: sourceKeyId } : { api_key: trimmedKey }),
      };

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

  const showKeySourceToggle =
    providerMode === 'existing' && form.provider_id !== '' && existingKeys.length > 0;
  const submitBusy = isPending || creatingProvider;

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
          <CustomButton type="default" onClick={onClose} disabled={submitBusy}>
            Cancel
          </CustomButton>
          <CustomButton
            type="primary"
            onClick={handleConfirm}
            loading={submitBusy}
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
          label={providerMode === 'new' && !hasKey ? 'Service type (optional)' : 'Service type'}
          options={SERVICE_TYPE_OPTIONS}
          value={form.service_type}
          onValueChange={handleServiceTypeChange}
          placeholder="Select a type"
          isRequired={providerMode === 'existing' || hasKey}
        />
        {providerMode === 'existing' ? (
          <div className="flex flex-col gap-1.5">
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
            {canCreateProvider && (
              <button
                type="button"
                onClick={handleEnterCreateProviderMode}
                className="self-start text-xs font-medium text-primary hover:underline"
              >
                <span className="inline-flex items-center gap-1">
                  <Plus className="size-3" />
                  Can’t find your provider? Create a new one
                </span>
              </button>
            )}
          </div>
        ) : (
          <div className="flex flex-col gap-3 rounded-md border border-dashed border-border p-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-foreground">New provider</span>
              <button
                type="button"
                onClick={handleExitCreateProviderMode}
                className="text-xs font-medium text-muted-foreground hover:text-foreground hover:underline"
              >
                ← Pick an existing provider
              </button>
            </div>
            <TextInput
              name="new_provider_display_name"
              label="Display name"
              value={newProvider.display_name}
              onChange={(e) => handleNewProviderDisplayName(e.target.value)}
              placeholder="e.g. OpenAI"
              isRequired
            />
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <TextInput
                name="new_provider_identifier"
                label="Identifier"
                value={newProvider.provider_id}
                onChange={(e) => {
                  setNewProviderTouched((prev) => ({ ...prev, provider_id: true }));
                  updateNewProvider('provider_id', e.target.value);
                }}
                placeholder="openai"
                helperText="Stable id used in pipeline code."
                isRequired
              />
              <TextInput
                name="new_provider_slug"
                label="Slug"
                value={newProvider.slug}
                onChange={(e) => {
                  setNewProviderTouched((prev) => ({ ...prev, slug: true }));
                  updateNewProvider('slug', e.target.value);
                }}
                placeholder="openai"
                helperText="URL-safe identifier."
                isRequired
              />
            </div>
            <TextInput
              name="new_provider_website"
              label="Website"
              value={newProvider.website_url}
              onChange={(e) => updateNewProvider('website_url', e.target.value)}
              placeholder="https://openai.com"
            />
            <TextAreaField
              name="new_provider_description"
              label="Description"
              value={newProvider.description}
              onChange={(e) => updateNewProvider('description', e.target.value)}
              rows={2}
              placeholder="Optional notes shown on the provider card."
            />
          </div>
        )}
        <TextInput
          name="label"
          label="Service name"
          value={form.label}
          onChange={(e) => update('label', e.target.value)}
          placeholder="e.g. OpenAI production"
        />
        <TextAreaField
          name="description"
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
            label={
              providerMode === 'new'
                ? 'API key (optional)'
                : showKeySourceToggle
                  ? 'New API key'
                  : 'API key'
            }
            type="password"
            value={form.api_key}
            onChange={(e) => update('api_key', e.target.value)}
            placeholder="sk-..."
            helperText={
              providerMode === 'new'
                ? 'Leave empty to register the provider now and add credentials later.'
                : undefined
            }
            isRequired={providerMode === 'existing'}
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
