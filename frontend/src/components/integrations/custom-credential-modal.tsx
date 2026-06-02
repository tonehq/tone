'use client';

import { CustomModal, SelectInput, TextInput } from '@/components/shared';
import { createCustomCredential, type CustomCredentialAuthKind } from '@/services/oauthService';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

const AUTH_KIND_OPTIONS = [
  { label: 'OAuth 2.0 (client credentials)', value: 'oauth2_client_credentials' },
  { label: 'Bearer Token', value: 'bearer' },
];

const schema = z
  .object({
    name: z.string().min(1, 'Credential name is required'),
    token_url: z.string().optional(),
    client_id: z.string().optional(),
    client_secret: z.string().optional(),
    scope: z.string().optional(),
    token: z.string().optional(),
  })
  .passthrough();

type FormData = z.infer<typeof schema>;

const EMPTY: FormData = {
  name: '',
  token_url: '',
  client_id: '',
  client_secret: '',
  scope: '',
  token: '',
};

interface CustomCredentialModalProps {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}

export default function CustomCredentialModal({
  open,
  onClose,
  onCreated,
}: CustomCredentialModalProps) {
  const { control, handleSubmit, reset, formState } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: EMPTY,
    mode: 'onChange',
  });

  const [authKind, setAuthKind] = useState<CustomCredentialAuthKind>('oauth2_client_credentials');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) {
      reset(EMPTY);
      setAuthKind('oauth2_client_credentials');
    }
  }, [open, reset]);

  const isOAuth = authKind === 'oauth2_client_credentials';

  const onFormSubmit = async (data: FormData) => {
    // Mirror the backend's required fields per auth kind before submitting.
    if (
      isOAuth &&
      (!data.token_url?.trim() || !data.client_id?.trim() || !data.client_secret?.trim())
    ) {
      showToast.error('Token URL, Client ID and Client Secret are required for OAuth 2.0');
      return;
    }
    if (!isOAuth && !data.token?.trim()) {
      showToast.error('Token is required for a Bearer credential');
      return;
    }
    setSaving(true);
    try {
      await createCustomCredential({
        name: data.name.trim(),
        auth_kind: authKind,
        ...(isOAuth
          ? {
              token_url: data.token_url?.trim(),
              client_id: data.client_id?.trim(),
              client_secret: data.client_secret?.trim(),
              scope: data.scope?.trim() || undefined,
            }
          : { token: data.token?.trim() }),
      });
      showToast.success('Custom credential created');
      reset(EMPTY);
      onCreated();
      onClose();
    } catch (err) {
      handleApiError(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <CustomModal
      open={open}
      onClose={onClose}
      title="New Custom Credential"
      description="Configure authentication for custom API endpoints."
      confirmText={saving ? 'Saving...' : 'Create credential'}
      onConfirm={handleSubmit(onFormSubmit)}
      confirmLoading={saving}
      confirmDisabled={!formState.isValid}
    >
      <div className="space-y-4">
        <SelectInput
          name="auth_kind"
          label="Authentication Type"
          options={AUTH_KIND_OPTIONS}
          value={authKind}
          onValueChange={(v) => setAuthKind(v as CustomCredentialAuthKind)}
          disabled={saving}
        />

        <TextInput
          name="name"
          control={control}
          label="Credential Name"
          placeholder="Enter credential name"
          isRequired
          disabled={saving}
        />

        {isOAuth ? (
          <>
            <TextInput
              name="token_url"
              control={control}
              label="Token URL"
              placeholder="https://auth.example.com/oauth/token"
              isRequired
              disabled={saving}
            />
            <TextInput
              name="client_id"
              control={control}
              label="Client ID"
              placeholder="Enter client ID"
              isRequired
              disabled={saving}
            />
            <TextInput
              name="client_secret"
              control={control}
              label="Client Secret"
              type="password"
              placeholder="Enter client secret"
              isRequired
              disabled={saving}
            />
            <TextInput
              name="scope"
              control={control}
              label="Scope"
              placeholder="e.g. read write (space separated, optional)"
              disabled={saving}
            />
          </>
        ) : (
          <TextInput
            name="token"
            control={control}
            label="Bearer Token"
            type="password"
            placeholder="Enter bearer token"
            isRequired
            disabled={saving}
          />
        )}
      </div>
    </CustomModal>
  );
}
