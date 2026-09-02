'use client';

import { AppLoader, CustomModal, SelectInput, TextInput } from '@/components/shared';
import { useChannel } from '@/lib/api/channels';
import type { Channel, ChannelUpsertPayload } from '@/types/integration';
import { handleApiError } from '@/utils/helpers';
import { useEffect, useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { ALL_FIELD_NAMES, CHANNEL_FIELDS, CHANNEL_TYPE_OPTIONS } from './channelFields';

type ChannelFormData = Record<string, string>;

const emptyValues = (): ChannelFormData =>
  ALL_FIELD_NAMES.reduce((acc, key) => ({ ...acc, [key]: '' }), {} as ChannelFormData);

interface ChannelFormModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (payload: ChannelUpsertPayload) => Promise<void>;
  editChannel?: Channel | null;
  providerKey?: string | null;
}

export default function ChannelFormModal({
  open,
  onClose,
  onSubmit,
  editChannel,
  providerKey,
}: ChannelFormModalProps) {
  const isEdit = Boolean(editChannel);
  const { control, handleSubmit, reset } = useForm<ChannelFormData>({
    defaultValues: emptyValues(),
    mode: 'onChange',
  });

  const [channelType, setChannelType] = useState('twilio');
  const [saving, setSaving] = useState(false);

  // Fetch the channel (with config) via the TanStack cache while the modal is
  // open in edit mode — mirrors sip-trunk-form-modal's useSipTrunk hydration.
  const {
    data: fullChannel,
    isLoading: hydrating,
    error: channelError,
  } = useChannel(open && editChannel ? editChannel.id : null, true);

  useEffect(() => {
    if (!open) return;
    if (!editChannel) {
      reset(emptyValues());
      setChannelType(providerKey ?? 'twilio');
      return;
    }
    setChannelType(editChannel.channel_type);
    if (fullChannel) {
      const config = (fullChannel.config ?? {}) as Record<string, string>;
      reset({ ...emptyValues(), name: fullChannel.name, ...config });
    }
  }, [open, editChannel, providerKey, fullChannel, reset]);

  // Preserve the previous catch: toast + fall back to the known name.
  useEffect(() => {
    if (open && editChannel && channelError) {
      handleApiError(channelError);
      reset({ ...emptyValues(), name: editChannel.name });
    }
  }, [open, editChannel, channelError, reset]);

  const fields = CHANNEL_FIELDS[channelType] ?? [];
  const values = useWatch({ control });
  const canSave =
    (values?.name ?? '').trim().length > 0 &&
    fields.every((f) => f.optional || (values?.[f.name] ?? '').trim().length > 0);

  const onFormSubmit = async (data: ChannelFormData) => {
    setSaving(true);
    try {
      const config = fields.reduce(
        (acc, f) => ({ ...acc, [f.name]: (data[f.name] ?? '').trim() }),
        {} as Record<string, string>,
      );
      await onSubmit({
        ...(editChannel ? { id: editChannel.id } : {}),
        name: (data.name ?? '').trim(),
        channel_type: channelType,
        config,
      });
      reset(emptyValues());
      onClose();
    } catch {
      // Intentionally swallowed: `onSubmit` (the channel-grid upsert handler)
      // already surfaces its own error toast. We only keep the modal open here
      // by NOT closing/resetting, so the user can retry.
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    reset(emptyValues());
    onClose();
  };

  return (
    <CustomModal
      open={open}
      onClose={handleCancel}
      title={isEdit ? 'Edit channel' : 'Add channel'}
      confirmText={saving ? 'Saving...' : 'Save'}
      onConfirm={handleSubmit(onFormSubmit)}
      confirmLoading={saving}
      confirmDisabled={!canSave || hydrating}
    >
      {hydrating ? (
        <AppLoader className="min-h-65" />
      ) : (
        <div className="space-y-4">
          <TextInput
            name="name"
            control={control}
            label="Name"
            placeholder="e.g. Production"
            rules={{ required: 'Name is required' }}
            isRequired
            disabled={saving}
          />
          <SelectInput
            name="channel-type"
            label="Type"
            options={CHANNEL_TYPE_OPTIONS}
            value={channelType}
            onValueChange={setChannelType}
            disabled={saving || !!providerKey || isEdit}
            helperText={
              isEdit
                ? 'Type cannot be changed after the channel is created.'
                : providerKey
                  ? 'Pre-selected from the provider tile.'
                  : undefined
            }
          />
          {fields.map((f) => (
            <TextInput
              key={f.name}
              name={f.name}
              control={control}
              label={f.label}
              type={f.type}
              placeholder={f.placeholder}
              helperText={f.helperText}
              rules={f.optional ? undefined : { required: `${f.label} is required` }}
              isRequired={!f.optional}
              disabled={saving}
            />
          ))}
        </div>
      )}
    </CustomModal>
  );
}
