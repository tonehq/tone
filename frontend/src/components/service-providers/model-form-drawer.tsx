'use client';

import { useEffect, useState } from 'react';

import {
  CheckboxField,
  CustomButton,
  CustomDrawer,
  SelectInput,
  TextAreaField,
  TextInput,
} from '@/components/shared';
import type { ModelUpsertPayload } from '@/services/servicesService';
import type { ProviderModel, ServiceKind } from '@/types/service';

import DrawerBackLink from './DrawerBackLink';

interface ModelFormDrawerProps {
  open: boolean;
  editing: ProviderModel | null;
  /** Defaults the kind dropdown when creating (usually first supported kind on the provider). */
  defaultKind?: ServiceKind | null;
  /** Restricts the kind dropdown to a subset (e.g. provider's supported kinds). */
  allowedKinds?: ServiceKind[];
  /**
   * When creating from a surface that isn't scoped to one provider (e.g. the
   * flat models table), pass the selectable providers to render a required
   * provider picker. Omit it on the provider detail page (provider is implied).
   */
  providers?: { id: string; display_name: string }[];
  /** Cloud providers the model can be hosted on (optional select). */
  cloudProviders?: { id: string; display_name: string }[];
  /** When set, renders a breadcrumb that navigates back to the detail view the
   * edit was launched from. Omit on the create flow (there's no detail to
   * return to). */
  onBack?: () => void;
  /** Label for the back breadcrumb (usually the model name). */
  backLabel?: string;
  onClose: () => void;
  /** `providerId` is only set when the provider picker is shown (create flow). */
  onSubmit: (payload: ModelUpsertPayload, id?: string, providerId?: string) => Promise<void>;
  isPending: boolean;
}

const ALL_KIND_OPTIONS: { value: ServiceKind; label: string }[] = [
  { value: 'llm', label: 'LLM' },
  { value: 'stt', label: 'Speech-to-Text' },
  { value: 'tts', label: 'Text-to-Speech' },
];

// Sentinel for "no cloud provider" (Radix Select can't use an empty-string
// item value). Maps to `null` in the payload.
const NO_CLOUD_PROVIDER = '__none__';

interface FormState {
  providerId: string;
  name: string;
  display_name: string;
  kind: ServiceKind | '';
  cloudProviderId: string;
  description: string;
  base_url: string;
  is_active: boolean;
}

function initialFormState(
  editing: ProviderModel | null,
  defaultKind: ServiceKind | null | undefined,
): FormState {
  if (!editing) {
    return {
      providerId: '',
      name: '',
      display_name: '',
      kind: defaultKind ?? '',
      cloudProviderId: NO_CLOUD_PROVIDER,
      description: '',
      base_url: '',
      is_active: true,
    };
  }
  return {
    providerId: '',
    name: editing.name,
    display_name: editing.display_name ?? '',
    kind: editing.kind,
    cloudProviderId: editing.cloud_provider_id ?? NO_CLOUD_PROVIDER,
    description: editing.description ?? '',
    base_url: editing.base_url ?? '',
    is_active: editing.is_active,
  };
}

export default function ModelFormDrawer({
  open,
  editing,
  defaultKind,
  allowedKinds,
  providers,
  cloudProviders,
  onBack,
  backLabel,
  onClose,
  onSubmit,
  isPending,
}: ModelFormDrawerProps) {
  const [form, setForm] = useState<FormState>(() => initialFormState(editing, defaultKind));

  useEffect(() => {
    if (open) setForm(initialFormState(editing, defaultKind));
  }, [open, editing, defaultKind]);

  const update = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const kindOptions =
    allowedKinds && allowedKinds.length > 0
      ? ALL_KIND_OPTIONS.filter((o) => allowedKinds.includes(o.value))
      : ALL_KIND_OPTIONS;

  // Show the provider picker only when creating from a non-scoped surface.
  const showProviderSelect = !editing && !!providers?.length;
  const providerOptions = (providers ?? []).map((p) => ({ value: p.id, label: p.display_name }));

  const cloudProviderOptions = [
    { value: NO_CLOUD_PROVIDER, label: 'None' },
    ...(cloudProviders ?? []).map((p) => ({ value: p.id, label: p.display_name })),
  ];

  const trimmedName = form.name.trim();
  const canSubmit =
    trimmedName.length > 0 && form.kind !== '' && (!showProviderSelect || form.providerId !== '');

  const handleConfirm = async () => {
    if (!canSubmit) return;
    const payload: ModelUpsertPayload = {
      name: trimmedName,
      display_name: form.display_name.trim() || undefined,
      kind: form.kind as ServiceKind,
      cloud_provider_id: form.cloudProviderId === NO_CLOUD_PROVIDER ? null : form.cloudProviderId,
      description: form.description.trim() || undefined,
      base_url: form.base_url.trim() || undefined,
      is_active: form.is_active,
    };
    await onSubmit(payload, editing?.id, showProviderSelect ? form.providerId : undefined);
  };

  return (
    <CustomDrawer
      open={open}
      onClose={onClose}
      title={editing ? 'Edit model' : 'Add model'}
      description={
        editing
          ? 'Update model details. The name must remain unique within the provider.'
          : 'Register a new model under this provider. It will appear in the global catalog.'
      }
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
            Save
          </CustomButton>
        </div>
      }
    >
      <div className="flex flex-col gap-4 pt-1">
        {onBack && <DrawerBackLink onClick={onBack} label={backLabel} />}
        {showProviderSelect && (
          <SelectInput
            name="providerId"
            label="Model provider"
            options={providerOptions}
            value={form.providerId}
            onValueChange={(v) => update('providerId', v)}
            placeholder="Select a model provider"
            isRequired
          />
        )}
        <SelectInput
          name="cloudProviderId"
          label="Cloud provider"
          options={cloudProviderOptions}
          value={form.cloudProviderId}
          onValueChange={(v) => update('cloudProviderId', v)}
          placeholder="Where the model is hosted"
        />
        <TextInput
          name="name"
          label="Model name"
          value={form.name}
          onChange={(e) => update('name', e.target.value)}
          placeholder="e.g. gpt-4o-mini"
          isRequired
        />
        <TextInput
          name="display_name"
          label="Display name"
          value={form.display_name}
          onChange={(e) => update('display_name', e.target.value)}
          placeholder="Optional — shown in lists"
        />
        <SelectInput
          name="kind"
          label="Kind"
          options={kindOptions}
          value={form.kind}
          onValueChange={(v) => update('kind', v as ServiceKind)}
          placeholder="Select a kind"
          isRequired
        />
        <TextAreaField
          name="description"
          label="Description"
          value={form.description}
          onChange={(e) => update('description', e.target.value)}
          rows={3}
          placeholder="Short summary of the model."
        />
        <TextInput
          name="base_url"
          label="Base URL"
          value={form.base_url}
          onChange={(e) => update('base_url', e.target.value)}
          placeholder="Optional — overrides the provider default endpoint"
        />
        <CheckboxField
          id="is_active"
          label="Active"
          checked={form.is_active}
          onCheckedChange={(v) => update('is_active', !!v)}
        />
      </div>
    </CustomDrawer>
  );
}
