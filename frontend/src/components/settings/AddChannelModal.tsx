'use client';

import { CustomModal, SelectInput, TextInput } from '@/components/shared';
import { type AddChannelFormData, addChannelSchema } from '@/schemas/settings';
import type { IntegrationRow } from '@/types/integration';
import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';

const CHANNEL_TYPE_OPTIONS = [
  { label: 'Twilio', value: 'twilio' },
  { label: 'Telnyx', value: 'telnyx' },
  { label: 'Exotel', value: 'exotel' },
];

interface AddChannelModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: {
    id?: number;
    name: string;
    type: string;
    auth_token: string;
    account_sid: string;
  }) => Promise<void>;
  editData?: IntegrationRow | null;
  providerKey?: string | null;
}

export default function AddChannelModal({
  open,
  onClose,
  onSubmit,
  editData,
  providerKey,
}: AddChannelModalProps) {
  const isEdit = Boolean(editData);

  const { control, handleSubmit, reset, formState } = useForm<AddChannelFormData>({
    resolver: zodResolver(addChannelSchema),
    defaultValues: { name: '', auth_token: '', account_sid: '' },
  });

  const [type, setType] = useState('twilio');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open && editData) {
      reset({
        name: editData.name,
        auth_token: editData.auth_token,
        account_sid: editData.account_sid,
      });
      setType(editData.type ?? 'twilio');
    } else if (open) {
      reset({ name: '', auth_token: '', account_sid: '' });
      setType(providerKey ?? 'twilio');
    }
  }, [open, editData, providerKey, reset]);

  const onFormSubmit = async (data: AddChannelFormData) => {
    setSaving(true);
    try {
      await onSubmit({
        ...(editData ? { id: editData.id } : {}),
        name: data.name.trim(),
        type,
        auth_token: data.auth_token.trim(),
        account_sid: data.account_sid.trim(),
      });
      reset({ name: '', auth_token: '', account_sid: '' });
      onClose();
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    reset({ name: '', auth_token: '', account_sid: '' });
    onClose();
  };

  return (
    <CustomModal
      open={open}
      onClose={handleCancel}
      title={isEdit ? 'Edit API key' : 'Add new API key'}
      confirmText={saving ? 'Saving...' : 'Save'}
      onConfirm={handleSubmit(onFormSubmit)}
      confirmLoading={saving}
      confirmDisabled={!formState.isValid}
    >
      <div className="space-y-4">
        <TextInput
          name="name"
          control={control}
          label="Name"
          placeholder="e.g. Twilio Production"
          isRequired
          disabled={saving}
        />
        <SelectInput
          name="channel-type"
          label="Type"
          options={CHANNEL_TYPE_OPTIONS}
          value={type}
          onValueChange={setType}
          disabled={saving || !!providerKey || isEdit}
        />
        <TextInput
          name="auth_token"
          control={control}
          label="Auth Token"
          type="password"
          placeholder="Enter auth token"
          isRequired
          disabled={saving}
        />
        <TextInput
          name="account_sid"
          control={control}
          label="Account SID"
          placeholder="Enter account SID"
          isRequired
          disabled={saving}
        />
      </div>
    </CustomModal>
  );
}
