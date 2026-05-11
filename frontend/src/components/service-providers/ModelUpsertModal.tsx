'use client';

import { CustomModal, SelectInput, TextAreaField, TextInput } from '@/components/shared';
import { type ModelUpsertFormData, modelUpsertSchema } from '@/schemas/provider';
import type { ModelUpsertPayload, ServiceProviderModel } from '@/types/provider';
import { zodResolver } from '@hookform/resolvers/zod';
import { useCallback, useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';

const STATUS_OPTIONS = [
  { value: 'active', label: 'Active' },
  { value: 'inactive', label: 'Inactive' },
];

interface ModelUpsertModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (payload: ModelUpsertPayload) => Promise<void>;
  serviceProviderId: number;
  defaultServiceType?: string;
  providerApiKeyId?: number | null;
  model?: ServiceProviderModel | null;
}

const MODAL_CLASS =
  '[&>div:first-child]:pt-3 [&>div:first-child]:pb-1 [&_[data-slot=dialog-description]]:mt-0.5';
const LABEL_COMPACT = '[&_label]:mb-1 [&_label]:text-xs';

export default function ModelUpsertModal({
  open,
  onClose,
  onSubmit,
  serviceProviderId,
  defaultServiceType,
  providerApiKeyId,
  model,
}: ModelUpsertModalProps) {
  const isEdit = !!model;

  const { control, handleSubmit, reset, formState } = useForm<ModelUpsertFormData>({
    resolver: zodResolver(modelUpsertSchema),
    defaultValues: { name: '' },
  });

  const [status, setStatus] = useState('active');
  const [metaDataStr, setMetaDataStr] = useState('');
  const [saving, setSaving] = useState(false);
  const [metaError, setMetaError] = useState('');

  useEffect(() => {
    if (open) {
      if (model) {
        reset({ name: model.name });
        setStatus(model.status ?? 'active');
        setMetaDataStr(model.meta_data ? JSON.stringify(model.meta_data, null, 2) : '');
      } else {
        reset({ name: '' });
        setStatus('active');
        setMetaDataStr('');
      }
      setMetaError('');
    }
  }, [open, model, reset]);

  const onFormSubmit = useCallback(
    async (data: ModelUpsertFormData) => {
      let metaData: Record<string, unknown> | undefined;
      if (metaDataStr.trim()) {
        try {
          metaData = JSON.parse(metaDataStr.trim());
          setMetaError('');
        } catch {
          setMetaError('Invalid JSON format');
          return;
        }
      }

      setSaving(true);
      try {
        const payload: ModelUpsertPayload = {
          service_provider_id: serviceProviderId,
          name: data.name.trim(),
          service_type: defaultServiceType,
          status,
          meta_data: metaData,
          api_key_id: providerApiKeyId ?? null,
        };
        if (isEdit) payload.id = model.id;
        await onSubmit(payload);
        onClose();
      } finally {
        setSaving(false);
      }
    },
    [
      metaDataStr,
      serviceProviderId,
      defaultServiceType,
      providerApiKeyId,
      isEdit,
      model,
      status,
      onSubmit,
      onClose,
    ],
  );

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Edit Model' : 'Add Model'}
      description={
        isEdit ? 'Update this model configuration.' : 'Add a new model to this provider.'
      }
      confirmText={isEdit ? 'Save Changes' : 'Create Model'}
      onConfirm={handleSubmit(onFormSubmit)}
      confirmLoading={saving}
      confirmDisabled={!formState.isValid}
      width="sm:max-w-lg"
      className={MODAL_CLASS}
      contentClassName={`pt-2 pb-3 ${LABEL_COMPACT}`}
    >
      <div className="flex flex-col gap-2.5">
        <div className="grid grid-cols-2 gap-3">
          <TextInput
            name="name"
            control={control}
            label="Model Name"
            placeholder="e.g. gpt-4o"
            isRequired
          />
          <SelectInput
            name="model-status"
            label="Status"
            options={STATUS_OPTIONS}
            value={status}
            onValueChange={setStatus}
          />
        </div>

        <TextAreaField
          name="model-metadata"
          label="Metadata (JSON)"
          placeholder='{"model": "gpt-4o"}'
          value={metaDataStr}
          onChange={(e) => {
            setMetaDataStr(e.target.value);
            if (metaError) setMetaError('');
          }}
          rows={3}
          className="font-mono"
          error={!!metaError}
          helperText={metaError || undefined}
        />
      </div>
    </CustomModal>
  );
}
