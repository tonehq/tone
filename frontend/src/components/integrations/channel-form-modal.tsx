'use client';

import { AppLoader, CustomModal, SelectInput, TextInput } from '@/components/shared';
import { getChannel } from '@/services/channelService';
import type { Channel, ChannelUpsertPayload } from '@/types/integration';
import { handleApiError } from '@/utils/helpers';
import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

// Only providers that use the account_sid + auth_token credential shape
// rendered by this form. Telnyx / Exotel use different credential schemas
// and need their own field set before they can be added here.
const CHANNEL_TYPE_OPTIONS = [{ label: 'Twilio', value: 'twilio' }];

const channelFormSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  auth_token: z.string().min(1, 'Auth token is required'),
  account_sid: z.string().min(1, 'Account SID is required'),
});

type ChannelFormData = z.infer<typeof channelFormSchema>;

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
  const { control, handleSubmit, reset, formState } = useForm<ChannelFormData>({
    resolver: zodResolver(channelFormSchema),
    defaultValues: { name: '', auth_token: '', account_sid: '' },
    mode: 'onChange',
  });

  const [channelType, setChannelType] = useState('twilio');
  const [saving, setSaving] = useState(false);
  const [hydrating, setHydrating] = useState(false);

  useEffect(() => {
    if (!open) return;
    if (editChannel) {
      setChannelType(editChannel.channel_type);
      setHydrating(true);
      getChannel(editChannel.id, true)
        .then((full) => {
          const config = (full.config ?? {}) as Record<string, string>;
          reset({
            name: full.name,
            auth_token: config.auth_token ?? '',
            account_sid: config.account_sid ?? '',
          });
        })
        .catch((err) => {
          handleApiError(err);
          reset({ name: editChannel.name, auth_token: '', account_sid: '' });
        })
        .finally(() => setHydrating(false));
    } else {
      reset({ name: '', auth_token: '', account_sid: '' });
      setChannelType(providerKey ?? 'twilio');
    }
  }, [open, editChannel, providerKey, reset]);

  const onFormSubmit = async (data: ChannelFormData) => {
    setSaving(true);
    try {
      await onSubmit({
        ...(editChannel ? { id: editChannel.id } : {}),
        name: data.name.trim(),
        channel_type: channelType,
        config: {
          auth_token: data.auth_token.trim(),
          account_sid: data.account_sid.trim(),
        },
      });
      reset({ name: '', auth_token: '', account_sid: '' });
      onClose();
    } catch {
      // Error already surfaced by the caller via handleApiError.
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
      title={isEdit ? 'Edit channel' : 'Add channel'}
      confirmText={saving ? 'Saving...' : 'Save'}
      onConfirm={handleSubmit(onFormSubmit)}
      confirmLoading={saving}
      confirmDisabled={!formState.isValid || hydrating}
    >
      {hydrating ? (
        <AppLoader className="min-h-[260px]" />
      ) : (
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
      )}
    </CustomModal>
  );
}
