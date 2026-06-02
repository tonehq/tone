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

interface ModelFormDrawerProps {
  open: boolean;
  editing: ProviderModel | null;
  /** Defaults the kind dropdown when creating (usually first supported kind on the provider). */
  defaultKind?: ServiceKind | null;
  /** Restricts the kind dropdown to a subset (e.g. provider's supported kinds). */
  allowedKinds?: ServiceKind[];
  onClose: () => void;
  onSubmit: (payload: ModelUpsertPayload, id?: string) => Promise<void>;
  isPending: boolean;
}

const ALL_KIND_OPTIONS: { value: ServiceKind; label: string }[] = [
  { value: 'llm', label: 'LLM' },
  { value: 'stt', label: 'Speech-to-Text' },
  { value: 'tts', label: 'Text-to-Speech' },
];

interface FormState {
  name: string;
  display_name: string;
  kind: ServiceKind | '';
  description: string;
  is_active: boolean;
}

function initialFormState(
  editing: ProviderModel | null,
  defaultKind: ServiceKind | null | undefined,
): FormState {
  if (!editing) {
    return {
      name: '',
      display_name: '',
      kind: defaultKind ?? '',
      description: '',
      is_active: true,
    };
  }
  return {
    name: editing.name,
    display_name: editing.display_name ?? '',
    kind: editing.kind,
    description: editing.description ?? '',
    is_active: editing.is_active,
  };
}

export default function ModelFormDrawer({
  open,
  editing,
  defaultKind,
  allowedKinds,
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

  const trimmedName = form.name.trim();
  const canSubmit = trimmedName.length > 0 && form.kind !== '';

  const handleConfirm = async () => {
    if (!canSubmit) return;
    const payload: ModelUpsertPayload = {
      name: trimmedName,
      display_name: form.display_name.trim() || undefined,
      kind: form.kind as ServiceKind,
      description: form.description.trim() || undefined,
      is_active: form.is_active,
    };
    await onSubmit(payload, editing?.id);
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
