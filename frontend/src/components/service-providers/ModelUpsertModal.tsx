'use client';

import { CustomModal, SelectInput, TextInput } from '@/components/shared';
import type { ModelUpsertPayload, ServiceProviderModel } from '@/types/provider';
import { useCallback, useEffect, useState } from 'react';

const SERVICE_TYPE_OPTIONS = [
  { value: 'llm', label: 'LLM' },
  { value: 'stt', label: 'STT' },
  { value: 'tts', label: 'TTS' },
];

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
  model,
}: ModelUpsertModalProps) {
  const isEdit = !!model;

  const [name, setName] = useState('');
  const [serviceType, setServiceType] = useState(defaultServiceType ?? 'llm');
  const [status, setStatus] = useState('active');
  const [metaDataStr, setMetaDataStr] = useState('');
  const [saving, setSaving] = useState(false);
  const [metaError, setMetaError] = useState('');

  useEffect(() => {
    if (open) {
      if (model) {
        setName(model.name);
        setServiceType(model.service_type ?? defaultServiceType ?? 'llm');
        setStatus(model.status ?? 'active');
        setMetaDataStr(model.meta_data ? JSON.stringify(model.meta_data, null, 2) : '');
      } else {
        setName('');
        setServiceType(defaultServiceType ?? 'llm');
        setStatus('active');
        setMetaDataStr('');
      }
      setMetaError('');
    }
  }, [open, model, defaultServiceType]);

  const handleSubmit = useCallback(async () => {
    if (!name.trim()) return;

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
        name: name.trim(),
        service_type: serviceType,
        status,
        meta_data: metaData,
      };
      if (isEdit) payload.id = model.id;
      await onSubmit(payload);
      onClose();
    } finally {
      setSaving(false);
    }
  }, [name, serviceType, status, metaDataStr, serviceProviderId, isEdit, model, onSubmit, onClose]);

  const isValid = name.trim().length > 0;

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Edit Model' : 'Add Model'}
      description={
        isEdit ? 'Update this model configuration.' : 'Add a new model to this provider.'
      }
      confirmText={isEdit ? 'Save Changes' : 'Create Model'}
      onConfirm={handleSubmit}
      confirmLoading={saving}
      confirmDisabled={!isValid}
      width="sm:max-w-lg"
      className={MODAL_CLASS}
      contentClassName={`pt-2 pb-3 ${LABEL_COMPACT}`}
    >
      <div className="flex flex-col gap-2.5">
        <TextInput
          name="model-name"
          label="Model Name"
          placeholder="e.g. gpt-4o"
          value={name}
          onChange={(e) => setName(e.target.value)}
          isRequired
        />

        <div className="grid grid-cols-2 gap-3">
          <SelectInput
            name="model-service-type"
            label="Service Type"
            options={SERVICE_TYPE_OPTIONS}
            value={serviceType}
            onValueChange={setServiceType}
          />
          <SelectInput
            name="model-status"
            label="Status"
            options={STATUS_OPTIONS}
            value={status}
            onValueChange={setStatus}
          />
        </div>

        <div>
          <label
            htmlFor="model-metadata"
            className="mb-1 block text-xs font-medium text-foreground"
          >
            Metadata (JSON)
          </label>
          <textarea
            id="model-metadata"
            value={metaDataStr}
            onChange={(e) => {
              setMetaDataStr(e.target.value);
              if (metaError) setMetaError('');
            }}
            placeholder='{"context_window": 128000}'
            rows={3}
            className="w-full resize-none rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:border-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30 font-mono"
          />
          {metaError && <p className="mt-1 text-xs text-destructive">{metaError}</p>}
        </div>
      </div>
    </CustomModal>
  );
}
