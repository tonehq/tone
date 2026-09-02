'use client';

/**
 * Create / edit page for ``app_integrations`` — the global catalog of
 * third-party providers Tone supports.
 *
 * The page is intentionally split into three sections (Basic info, Auth,
 * Configuration) to match the mental model of "what does the user need to
 * fill in" rather than the underlying column layout. OAuth-specific fields
 * are conditionally revealed only when ``auth_type === 'oauth'`` so the form
 * stays focused for PAT / no-auth providers.
 *
 * Reuses the shared form primitives (TextInput, SelectInput, CheckboxField,
 * TextAreaField, CustomButton) and follows the same coding standards as
 * :file:`frontend/src/components/mcp/MCPFormPage.tsx`.
 */

import {
  CustomButton,
  CustomModal,
  SelectInput,
  TextAreaField,
  TextInput,
} from '@/components/shared';
import CheckboxField from '@/components/shared/CheckboxField';
import { useGoBack } from '@/hooks/useGoBack';
import {
  useAppIntegration,
  useCreateAppIntegration,
  useDeleteAppIntegration,
  useUpdateAppIntegration,
} from '@/lib/api/appIntegrations';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { ArrowLeft, KeyRound, Loader2, Save, Settings2, Sparkles, Trash2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';

import CallbackUrlField from './CallbackUrlField';
import AppIntegrationSection from './AppIntegrationSection';
import {
  AUTH_TYPE_OPTIONS,
  CATEGORY_OPTIONS,
  DEFAULT_STATE,
  SLUG_RULE,
  type FormState,
} from './appIntegrationFormConstants';
import { formStateFromRow, serializePayload } from './appIntegrationFormHelpers';

interface AppIntegrationFormPageProps {
  integrationId?: string;
}

export default function AppIntegrationFormPage({ integrationId }: AppIntegrationFormPageProps) {
  const router = useRouter();
  const isEditMode = Boolean(integrationId);

  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);

  const { control, handleSubmit, reset } = useForm<FormState>({
    defaultValues: DEFAULT_STATE,
    mode: 'onBlur',
  });

  // Loaded row metadata (from the TanStack cache) — used to gate the Delete
  // button (default rows are protected by the backend) and to show a friendly
  // name in the confirm modal.
  const {
    data: loadedRow,
    isLoading: loading,
    error: loadError,
  } = useAppIntegration(integrationId);
  const { mutateAsync: createIntegration, isPending: creating } = useCreateAppIntegration();
  const { mutateAsync: updateIntegration, isPending: updating } = useUpdateAppIntegration();
  const { mutateAsync: deleteIntegration, isPending: deleting } = useDeleteAppIntegration();
  const saving = creating || updating;

  // Hydrate the form when the edited integration loads.
  useEffect(() => {
    if (loadedRow) reset(formStateFromRow(loadedRow));
  }, [loadedRow, reset]);

  // Preserve the previous toast-on-fetch-error behavior.
  useEffect(() => {
    if (loadError) handleApiError(loadError);
  }, [loadError]);

  // Conditionally show OAuth-specific fields. ``useWatch`` (vs ``watch()``)
  // keeps the parent render-list stable; only the dependent block re-renders.
  const authType = useWatch({ control, name: 'auth_type' });
  const watchedSlug = useWatch({ control, name: 'slug' });
  const isOAuth = authType === 'oauth';

  const onSave = async (values: FormState) => {
    try {
      const payload = serializePayload(values);
      if (isEditMode && integrationId) {
        await updateIntegration({ id: integrationId, payload });
        showToast.success('Integration updated');
      } else {
        await createIntegration(payload);
        showToast.success('Integration created');
      }
      router.push('/settings/integrations');
    } catch (err) {
      handleApiError(err);
    }
  };

  const onBack = useGoBack('/settings/integrations');

  /**
   * Delete the integration. Backend already rejects ``is_default`` rows with a
   * clear 400; we additionally hide the button for those, so this only fires
   * for admin-created rows.
   */
  const onDelete = async () => {
    if (!integrationId) return;
    try {
      await deleteIntegration(integrationId);
      showToast.success('Integration deleted');
      router.push('/settings/integrations');
    } catch (err) {
      handleApiError(err);
    } finally {
      setConfirmDeleteOpen(false);
    }
  };

  // Default rows are seed-managed (Google, HubSpot, …); the backend protects
  // them from deletion. Mirror that here so the button doesn't appear at all.
  const canDelete = isEditMode && !!loadedRow && !loadedRow.is_default;

  const headerTitle = useMemo(
    () => (isEditMode ? 'Edit integration' : 'New integration'),
    [isEditMode],
  );

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      {/* Top bar */}
      <div className="relative flex shrink-0 items-center justify-between gap-3 border-b border-border bg-background px-6 py-3">
        <div className="flex min-w-0 items-center gap-3">
          <CustomButton
            type="text"
            size="icon-sm"
            onClick={onBack}
            aria-label="Back to integrations"
            className="shrink-0 text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft size={16} />
          </CustomButton>
          <div className="min-w-0">
            <h1 className="truncate text-[15px] font-semibold tracking-tight text-foreground">
              {headerTitle}
            </h1>
            <p className="truncate text-[11.5px] text-muted-foreground">
              Add a third-party provider that your agents can use to read or act on external data.
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          {canDelete && (
            <CustomButton
              type="default"
              size="sm"
              onClick={() => setConfirmDeleteOpen(true)}
              disabled={saving || deleting}
              icon={<Trash2 size={13} className="text-destructive" />}
              className="text-destructive"
            >
              Delete
            </CustomButton>
          )}
          <CustomButton type="default" size="sm" onClick={onBack} disabled={saving}>
            Cancel
          </CustomButton>
          <CustomButton
            type="primary"
            size="sm"
            icon={saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
            onClick={handleSubmit(onSave)}
            loading={saving}
            disabled={loading}
          >
            {isEditMode ? 'Save changes' : 'Create'}
          </CustomButton>
        </div>
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 -bottom-px h-px bg-gradient-to-r from-transparent via-primary/60 to-transparent"
        />
      </div>

      {/* Body */}
      <div className="min-h-0 flex-1 overflow-y-auto bg-muted/30">
        <div className="mx-auto w-full max-w-3xl space-y-5 px-6 py-7">
          {loading ? (
            <div className="flex items-center justify-center py-24 text-muted-foreground">
              <Loader2 className="mr-2 size-4 animate-spin" />
              <span className="text-sm">Loading integration…</span>
            </div>
          ) : (
            <>
              <AppIntegrationSection
                icon={<Sparkles size={14} className="text-violet-500" />}
                title="Basic info"
                description="What this integration is and how it appears in the catalog."
              >
                <TextInput
                  name="slug"
                  control={control}
                  rules={SLUG_RULE}
                  label="Slug"
                  placeholder="hubspot, google_calendar, github…"
                  isRequired
                  disabled={isEditMode /* slug is the public identifier — discourage changes */}
                  className="font-mono"
                  helperText={
                    isEditMode
                      ? "Locked — it's part of the callback URL you registered with the provider."
                      : 'Used in the callback URL. Choose carefully — cannot be changed later.'
                  }
                />
                <TextInput
                  name="display_name"
                  control={control}
                  rules={{ required: 'Display name is required', maxLength: 120 }}
                  label="Display name"
                  placeholder="HubSpot, Google Calendar, GitHub…"
                  isRequired
                />
                <TextAreaField
                  name="description"
                  control={control}
                  label="Description"
                  placeholder="Short blurb shown next to the provider's name."
                  rows={3}
                />
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <SelectInput
                    name="category"
                    control={control}
                    label="Category"
                    options={CATEGORY_OPTIONS}
                    placeholder="Pick a category"
                  />
                  <TextInput
                    name="icon_url"
                    control={control}
                    label="Icon URL"
                    placeholder="/icons/hubspot.svg or https://…"
                  />
                </div>
              </AppIntegrationSection>

              <AppIntegrationSection
                icon={<KeyRound size={14} className="text-muted-foreground" />}
                title="Authentication"
                description="How users will authorize this integration."
              >
                <SelectInput
                  name="auth_type"
                  control={control}
                  label="Auth type"
                  options={AUTH_TYPE_OPTIONS}
                  isRequired
                />

                {isOAuth && (
                  <div className="space-y-4 rounded-md border border-border/60 bg-muted/30 p-3.5">
                    {/* Tone's callback URL — admin must paste this into the
                        provider's OAuth app so the redirect after login is
                        allowed. Updates live as the slug field changes. */}
                    <CallbackUrlField slug={watchedSlug} />
                    <TextInput
                      name="auth_url"
                      control={control}
                      label="Authorization URL"
                      placeholder="https://provider.com/oauth/authorize"
                    />
                    <TextInput
                      name="token_url"
                      control={control}
                      label="Token URL"
                      placeholder="https://provider.com/oauth/token"
                    />
                    <TextInput
                      name="userinfo_url"
                      control={control}
                      label="User info URL"
                      placeholder="https://provider.com/oauth/userinfo"
                      helperText="Optional — called after login to capture the connecting user's email."
                    />
                    <TextAreaField
                      name="scopes"
                      control={control}
                      label="Scopes"
                      placeholder="comma- or newline-separated"
                      rows={3}
                      helperText="One scope per line, or comma-separated."
                    />
                    <CheckboxField
                      id="pkce_required"
                      control={control}
                      label="Require PKCE (recommended)"
                    />
                  </div>
                )}
              </AppIntegrationSection>

              <AppIntegrationSection
                icon={<Settings2 size={14} className="text-muted-foreground" />}
                title="Configuration"
                description="Where credentials live and how this integration is exposed."
              >
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <TextInput
                    name="client_id"
                    control={control}
                    type="password"
                    label="Client ID"
                    placeholder={isEditMode ? '••••••••  (leave blank to keep current)' : ''}
                    helperText="Encrypted at rest. Paste the value from the provider's dev portal."
                    className="font-mono"
                    autoComplete="off"
                  />
                  <TextInput
                    name="client_secret"
                    control={control}
                    type="password"
                    label="Client Secret"
                    placeholder={isEditMode ? '••••••••  (leave blank to keep current)' : ''}
                    helperText="Optional for public PKCE clients. Encrypted at rest."
                    className="font-mono"
                    autoComplete="off"
                  />
                </div>
                <TextAreaField
                  name="extra_auth_params"
                  control={control}
                  label="Extra auth params (JSON)"
                  placeholder='{"owner": "user"}'
                  rows={3}
                  helperText="Provider-specific query params. Leave blank for none."
                  className="font-mono text-[12.5px]"
                />
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <TextInput
                    name="sort_order"
                    control={control}
                    label="Sort order"
                    type="number"
                    helperText="Lower values appear first in the catalog."
                  />
                  <CheckboxField id="is_enabled" control={control} label="Enabled" />
                </div>
              </AppIntegrationSection>
            </>
          )}
        </div>
      </div>

      {/* Delete confirmation — gated above by ``canDelete`` so it never opens
          for default (seeded) rows the backend would reject anyway. */}
      <CustomModal
        open={confirmDeleteOpen}
        onClose={() => setConfirmDeleteOpen(false)}
        title={`Delete ${loadedRow?.display_name ?? 'integration'}?`}
        description={
          'This removes the integration from the catalog. Existing OAuth connections will be unlinked but kept. This action cannot be undone.'
        }
        confirmText="Delete"
        cancelText="Cancel"
        confirmType="primary"
        confirmLoading={deleting}
        onConfirm={onDelete}
      />
    </div>
  );
}
