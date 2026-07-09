'use client';

import { AppLoader, CustomModal, SelectInput, TextInput } from '@/components/shared';
import { getChannel } from '@/services/channelService';
import type { Channel, ChannelUpsertPayload } from '@/types/integration';
import { handleApiError } from '@/utils/helpers';
import { useEffect, useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';

interface ChannelField {
  name: string;
  label: string;
  type?: string;
  placeholder?: string;
}

const CHANNEL_FIELDS: Record<string, ChannelField[]> = {
  twilio: [
    { name: 'account_sid', label: 'Account SID', placeholder: 'Enter account SID' },
    { name: 'auth_token', label: 'Auth Token', type: 'password', placeholder: 'Enter auth token' },
  ],
  telnyx: [{ name: 'api_key', label: 'API Key', type: 'password', placeholder: 'Enter API key' }],
  plivo: [
    { name: 'auth_id', label: 'Auth ID', placeholder: 'Enter auth ID' },
    { name: 'auth_token', label: 'Auth Token', type: 'password', placeholder: 'Enter auth token' },
  ],
  exotel: [
    { name: 'account_sid', label: 'Account SID', placeholder: 'Enter account SID' },
    { name: 'api_key', label: 'API Key', placeholder: 'Enter API key' },
    { name: 'api_token', label: 'API Token', type: 'password', placeholder: 'Enter API token' },
    { name: 'subdomain', label: 'Subdomain', placeholder: 'e.g. api.exotel.com' },
  ],
  livekit: [
    { name: 'url', label: 'Server URL', placeholder: 'wss://your-project.livekit.cloud' },
    { name: 'api_key', label: 'API Key', placeholder: 'Enter API key' },
    { name: 'api_secret', label: 'API Secret', type: 'password', placeholder: 'Enter API secret' },
  ],
  daily: [{ name: 'api_key', label: 'API Key', type: 'password', placeholder: 'Enter API key' }],
};

const CHANNEL_TYPE_OPTIONS = [
  { label: 'Twilio', value: 'twilio' },
  { label: 'Telnyx', value: 'telnyx' },
  { label: 'Plivo', value: 'plivo' },
  { label: 'Exotel', value: 'exotel' },
  { label: 'LiveKit', value: 'livekit' },
  { label: 'Daily', value: 'daily' },
];

const ALL_FIELD_NAMES = [
  'name',
  'account_sid',
  'auth_token',
  'auth_id',
  'url',
  'api_key',
  'api_secret',
  'api_token',
  'subdomain',
];

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
  const [hydrating, setHydrating] = useState(false);

  useEffect(() => {
    if (!open) return;
    if (editChannel) {
      setChannelType(editChannel.channel_type);
      setHydrating(true);
      getChannel(editChannel.id, true)
        .then((full) => {
          const config = (full.config ?? {}) as Record<string, string>;
          reset({ ...emptyValues(), name: full.name, ...config });
        })
        .catch((err) => {
          handleApiError(err);
          reset({ ...emptyValues(), name: editChannel.name });
        })
        .finally(() => setHydrating(false));
    } else {
      reset(emptyValues());
      setChannelType(providerKey ?? 'twilio');
    }
  }, [open, editChannel, providerKey, reset]);

  const fields = CHANNEL_FIELDS[channelType] ?? [];
  const values = useWatch({ control });
  const canSave =
    (values?.name ?? '').trim().length > 0 &&
    fields.every((f) => (values?.[f.name] ?? '').trim().length > 0);

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
        <AppLoader className="min-h-[260px]" />
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
              rules={{ required: `${f.label} is required` }}
              isRequired
              disabled={saving}
            />
          ))}
        </div>
      )}
    </CustomModal>
  );
}
