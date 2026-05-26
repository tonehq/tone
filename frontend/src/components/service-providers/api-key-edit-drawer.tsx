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
import { Badge } from '@/components/ui/badge';
import type { Service, ServiceUpsertPayload } from '@/types/service';
import { cn } from '@/utils/cn';
import { handleApiError } from '@/utils/helpers';

import { TYPE_BADGE_STYLES } from './constants';

interface ApiKeyEditDrawerProps {
  open: boolean;
  editing: Service | null;
  /** Override drawer copy when opened from a different surface (e.g. the
   * listing page, where the card represents a provider connection). */
  title?: string;
  description?: string;
  /** When true, render an in-drawer spinner instead of the form. Used so the
   * drawer can pop open immediately while the parent fetches the key. */
  loading?: boolean;
  onClose: () => void;
  onSubmit: (payload: Partial<ServiceUpsertPayload>, id: string) => Promise<void>;
  isPending: boolean;
}

interface FormState {
  label: string;
  description: string;
  is_default: boolean;
  is_active: boolean;
}

function initialFormState(editing: Service | null): FormState {
  if (!editing) {
    return {
      label: '',
      description: '',
      is_default: false,
      is_active: true,
    };
  }
  return {
    label: editing.label ?? '',
    description: editing.description ?? '',
    is_default: editing.is_default,
    is_active: editing.is_active,
  };
}

export default function ApiKeyEditDrawer({
  open,
  editing,
  title = 'Edit API key',
  description = 'Update key details. To rotate the secret, delete this key and add a new one.',
  loading = false,
  onClose,
  onSubmit,
  isPending,
}: ApiKeyEditDrawerProps) {
  const [form, setForm] = useState<FormState>(() => initialFormState(editing));

  useEffect(() => {
    if (open) {
      setForm(initialFormState(editing));
    }
  }, [open, editing]);

  const update = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleConfirm = async () => {
    if (!editing) return;

    const payload: Partial<ServiceUpsertPayload> = {
      label: form.label.trim() || undefined,
      description: form.description.trim() || undefined,
      is_default: form.is_default,
      is_active: form.is_active,
    };

    try {
      await onSubmit(payload, editing.id);
    } catch (err) {
      handleApiError(err);
    }
  };

  return (
    <CustomDrawer
      open={open}
      onClose={onClose}
      title={title}
      description={description}
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
            disabled={loading || !editing}
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
          {editing && (
            <div className="flex flex-wrap items-center gap-2 rounded-md border border-border/70 bg-muted/30 px-3 py-2 text-xs">
              <span className="text-muted-foreground">Provider</span>
              <span className="font-medium text-foreground">
                {editing.provider?.display_name ?? '—'}
              </span>
              <span className="text-muted-foreground/40">·</span>
              <Badge
                className={cn(
                  'px-2 py-0 text-[10px] font-semibold uppercase tracking-wider',
                  TYPE_BADGE_STYLES[editing.service_type] ?? '',
                )}
              >
                {editing.service_type}
              </Badge>
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
            id="description"
            label="Description"
            value={form.description}
            onChange={(e) => update('description', e.target.value)}
            rows={2}
            placeholder="Optional notes for your team."
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
      )}
    </CustomDrawer>
  );
}
