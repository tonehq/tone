'use client';

import { CustomModal, SelectInput, TextInput } from '@/components/shared';
import { createCustomCredential, type CustomCredentialAuthKind } from '@/services/oauthService';
import type { OAuthConnection } from '@/types/oauth';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

const AUTH_KIND_OPTIONS = [
  { label: 'OAuth 2.0 (client credentials)', value: 'oauth2_client_credentials' },
  { label: 'Bearer Token', value: 'bearer' },
  { label: 'API Key', value: 'api_key' },
];

const schema = z
  .object({
    name: z.string().min(1, 'Credential name is required'),
    token_url: z.string().optional(),
    client_id: z.string().optional(),
    client_secret: z.string().optional(),
    scope: z.string().optional(),
    token: z.string().optional(),
    api_key: z.string().optional(),
    header_name: z.string().optional(),
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
  api_key: '',
  header_name: '',
};

interface CustomCredentialModalProps {
  open: boolean;
  onClose: () => void;
  /** Called after a successful create. Receives the new connection so callers
   * (e.g. the agent-config picker) can select it immediately. */
  onCreated: (created?: OAuthConnection) => void;
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
  const isApiKey = authKind === 'api_key';

  const onFormSubmit = async (data: FormData) => {
    // Mirror the backend's required fields per auth kind before submitting.
    if (
      isOAuth &&
      (!data.token_url?.trim() || !data.client_id?.trim() || !data.client_secret?.trim())
    ) {
      showToast.error('Token URL, Client ID and Client Secret are required for OAuth 2.0');
      return;
    }
    if (isApiKey && !data.api_key?.trim()) {
      showToast.error('API Key is required for an API Key credential');
      return;
    }
    if (!isOAuth && !isApiKey && !data.token?.trim()) {
      showToast.error('Token is required for a Bearer credential');
      return;
    }
    setSaving(true);
    try {
      const created = await createCustomCredential({
        name: data.name.trim(),
        auth_kind: authKind,
        ...(isOAuth
          ? {
              token_url: data.token_url?.trim(),
              client_id: data.client_id?.trim(),
              client_secret: data.client_secret?.trim(),
              scope: data.scope?.trim() || undefined,
            }
          : isApiKey
            ? {
                api_key: data.api_key?.trim(),
                header_name: data.header_name?.trim() || undefined,
              }
            : { token: data.token?.trim() }),
      });
      showToast.success('Custom credential created');
      reset(EMPTY);
      onCreated(created);
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
        ) : isApiKey ? (
          <>
            <TextInput
              name="header_name"
              control={control}
              label="Header Name"
              placeholder="X-API-Key"
              disabled={saving}
            />
            <TextInput
              name="api_key"
              control={control}
              label="API Key"
              type="password"
              placeholder="Enter API key"
              isRequired
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
