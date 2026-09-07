'use client';

import { useEffect, useState } from 'react';

import {
  CheckboxField,
  CustomButton,
  CustomDrawer,
  TextAreaField,
  TextInput,
} from '@/components/shared';
import type { CloudProvider, CloudProviderUpsertPayload } from '@/types/service';

interface CloudProviderEditDrawerProps {
  open: boolean;
  /** null → create; a row → edit. */
  editing: CloudProvider | null;
  onClose: () => void;
  onSubmit: (payload: CloudProviderUpsertPayload, id?: string) => Promise<void>;
  isPending: boolean;
}

interface FormState {
  provider_id: string;
  slug: string;
  display_name: string;
  website_url: string;
  description: string;
  is_active: boolean;
}

function initialFormState(editing: CloudProvider | null): FormState {
  if (!editing) {
    return {
      provider_id: '',
      slug: '',
      display_name: '',
      website_url: '',
      description: '',
      is_active: true,
    };
  }
  return {
    provider_id: editing.provider_id,
    slug: editing.slug,
    display_name: editing.display_name,
    website_url: editing.website_url ?? '',
    description: editing.description ?? '',
    is_active: editing.is_active,
  };
}

export default function CloudProviderEditDrawer({
  open,
  editing,
  onClose,
  onSubmit,
  isPending,
}: CloudProviderEditDrawerProps) {
  const [form, setForm] = useState<FormState>(() => initialFormState(editing));

  useEffect(() => {
    if (open) setForm(initialFormState(editing));
  }, [open, editing]);

  const update = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const canSubmit =
    form.provider_id.trim().length > 0 &&
    form.slug.trim().length > 0 &&
    form.display_name.trim().length > 0;

  const handleConfirm = async () => {
    if (!canSubmit) return;
    const payload: CloudProviderUpsertPayload = {
      provider_id: form.provider_id.trim(),
      slug: form.slug.trim(),
      display_name: form.display_name.trim(),
      website_url: form.website_url.trim() || undefined,
      description: form.description.trim() || undefined,
      is_active: form.is_active,
    };
    await onSubmit(payload, editing?.id);
  };

  return (
    <CustomDrawer
      open={open}
      onClose={onClose}
      title={editing ? 'Edit cloud provider' : 'Add cloud provider'}
      description={
        editing
          ? 'Update this cloud provider. It is a global catalog entry shared across organizations.'
          : 'Register a new cloud provider (the host a model runs on, e.g. AWS, Azure).'
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
        <TextInput
          name="provider_id"
          label="Provider ID"
          value={form.provider_id}
          onChange={(e) => update('provider_id', e.target.value)}
          placeholder="e.g. aws"
          isRequired
        />
        <TextInput
          name="slug"
          label="Slug"
          value={form.slug}
          onChange={(e) => update('slug', e.target.value)}
          placeholder="e.g. aws"
          isRequired
        />
        <TextInput
          name="display_name"
          label="Display name"
          value={form.display_name}
          onChange={(e) => update('display_name', e.target.value)}
          placeholder="e.g. AWS"
          isRequired
        />
        <TextInput
          name="website_url"
          label="Website"
          value={form.website_url}
          onChange={(e) => update('website_url', e.target.value)}
          placeholder="https://aws.amazon.com"
        />
        <TextAreaField
          name="description"
          label="Description"
          value={form.description}
          onChange={(e) => update('description', e.target.value)}
          rows={2}
          placeholder="Short description of the cloud provider."
        />
        <CheckboxField
          id="cloud_provider_is_active"
          label="Active — selectable when assigning models"
          checked={form.is_active}
          onCheckedChange={(v) => update('is_active', !!v)}
        />
      </div>
    </CustomDrawer>
  );
}
