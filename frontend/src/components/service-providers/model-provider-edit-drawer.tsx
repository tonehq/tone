'use client';

import { useEffect, useState } from 'react';

import {
  AppLoader,
  CheckboxField,
  CustomButton,
  CustomDrawer,
  TextAreaField,
  TextInput,
} from '@/components/shared';
import type { ModelProvider, ModelProviderUpsertPayload } from '@/types/service';
import { handleApiError } from '@/utils/helpers';

interface ModelProviderEditDrawerProps {
  open: boolean;
  editing: ModelProvider | null;
  /** When true, render an in-drawer spinner instead of the form. Used so the
   * drawer can pop open immediately while the parent fetches the record. */
  loading?: boolean;
  onClose: () => void;
  onSubmit: (providerId: string, payload: Partial<ModelProviderUpsertPayload>) => Promise<void>;
  isPending: boolean;
}

interface FormState {
  display_name: string;
  description: string;
  website_url: string;
  is_active: boolean;
}

function initialFormState(editing: ModelProvider | null): FormState {
  if (!editing) {
    return { display_name: '', description: '', website_url: '', is_active: true };
  }
  return {
    display_name: editing.display_name,
    description: editing.description ?? '',
    website_url: editing.website_url ?? '',
    is_active: editing.is_active,
  };
}

// Emit only fields the user actually changed so unaffected values aren't
// bounced through the PUT and, more importantly, we don't touch fields the
// current user has no permission to modify.
function diff(initial: FormState, current: FormState): Partial<ModelProviderUpsertPayload> {
  const out: Partial<ModelProviderUpsertPayload> = {};
  const name = current.display_name.trim();
  if (name && name !== initial.display_name.trim()) out.display_name = name;

  const desc = current.description.trim();
  if (desc !== initial.description.trim()) out.description = desc || undefined;

  const url = current.website_url.trim();
  if (url !== initial.website_url.trim()) out.website_url = url || undefined;

  if (current.is_active !== initial.is_active) out.is_active = current.is_active;

  return out;
}

export default function ModelProviderEditDrawer({
  open,
  editing,
  loading = false,
  onClose,
  onSubmit,
  isPending,
}: ModelProviderEditDrawerProps) {
  const [form, setForm] = useState<FormState>(() => initialFormState(editing));
  const [initial, setInitial] = useState<FormState>(() => initialFormState(editing));

  useEffect(() => {
    if (open) {
      const snap = initialFormState(editing);
      setForm(snap);
      setInitial(snap);
    }
  }, [open, editing]);

  const update = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const canSubmit = form.display_name.trim().length > 0;

  const handleConfirm = async () => {
    if (!editing || !canSubmit) return;
    const payload = diff(initial, form);
    if (Object.keys(payload).length === 0) {
      // No changes — close silently, don't waste a PUT.
      onClose();
      return;
    }
    try {
      await onSubmit(editing.id, payload);
    } catch (err) {
      handleApiError(err);
    }
  };

  return (
    <CustomDrawer
      open={open}
      onClose={onClose}
      title="Edit provider"
      description="Update this provider's display details. API keys and models are managed on the provider page."
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
            disabled={loading || !editing || !canSubmit}
          >
            Save
          </CustomButton>
        </div>
      }
    >
      {loading && !editing ? (
        <AppLoader className="min-h-0 flex-1 py-16" />
      ) : (
        <div className="flex flex-col gap-4 pt-1">
          <TextInput
            name="display_name"
            label="Display name"
            value={form.display_name}
            onChange={(e) => update('display_name', e.target.value)}
            placeholder="e.g. OpenAI"
            isRequired
          />
          <TextInput
            name="website_url"
            label="Website"
            value={form.website_url}
            onChange={(e) => update('website_url', e.target.value)}
            placeholder="https://openai.com"
          />
          <TextAreaField
            name="description"
            label="Description"
            value={form.description}
            onChange={(e) => update('description', e.target.value)}
            rows={2}
            placeholder="Short description shown on the provider card."
          />
          <CheckboxField
            id="is_active"
            label="Active — visible to orgs when adding API keys"
            checked={form.is_active}
            onCheckedChange={(v) => update('is_active', !!v)}
          />
        </div>
      )}
    </CustomDrawer>
  );
}
