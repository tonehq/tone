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

import { CustomButton, SelectInput, TextAreaField, TextInput } from '@/components/shared';
import CheckboxField from '@/components/shared/CheckboxField';
import { useGoBack } from '@/hooks/useGoBack';
import {
  createAppIntegration,
  getAppIntegration,
  updateAppIntegration,
} from '@/services/appIntegrationService';
import type {
  AppIntegration,
  AppIntegrationAuthType,
  AppIntegrationCreatePayload,
} from '@/types/appIntegration';
import { handleApiError } from '@/utils/helpers';
import { showToast } from '@/utils/toast';
import { ArrowLeft, KeyRound, Loader2, Save, Settings2, Sparkles } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';

interface FormState {
  slug: string;
  display_name: string;
  description: string;
  category: string;
  icon_url: string;
  auth_type: AppIntegrationAuthType;
  auth_url: string;
  token_url: string;
  scopes: string; // comma- or newline-separated; serialized to string[] on submit
  client_id_env_key: string;
  client_secret_env_key: string;
  pkce_required: boolean;
  is_enabled: boolean;
  sort_order: number;
  extra_auth_params: string; // raw JSON; parsed on submit
}

// Radix Select reserves the empty string for "no selection". So when the user
// hasn't picked a category, the form state stays as ``NO_CATEGORY`` and we
// translate it to ``null`` on submit (and back on hydrate). Lets us still
// expose a real "Uncategorized" entry while keeping the placeholder UX intact.
const NO_CATEGORY = '__none__';

const DEFAULT_STATE: FormState = {
  slug: '',
  display_name: '',
  description: '',
  category: NO_CATEGORY,
  icon_url: '',
  auth_type: 'oauth',
  auth_url: '',
  token_url: '',
  scopes: '',
  client_id_env_key: '',
  client_secret_env_key: '',
  pkce_required: true,
  is_enabled: true,
  sort_order: 100,
  extra_auth_params: '',
};

// Single source of truth for both the OAuth-flow shape AND the credential
// format. Kept flat (not nested across two selects) because a single choice
// fully describes how the integration authenticates.
const AUTH_TYPE_OPTIONS = [
  { value: 'oauth', label: 'OAuth — provider login flow' },
  { value: 'api_key', label: 'API key — paste a static key in a custom header' },
  { value: 'bearer_token', label: 'Bearer token — paste a static token (e.g. PAT)' },
  { value: 'none', label: 'No auth — public / unauthenticated' },
];

const CATEGORY_OPTIONS = [
  { value: NO_CATEGORY, label: 'Uncategorized' },
  { value: 'crm', label: 'CRM' },
  { value: 'calendar', label: 'Calendar' },
  { value: 'communication', label: 'Communication' },
  { value: 'dev_tools', label: 'Developer Tools' },
  { value: 'storage', label: 'Storage' },
  { value: 'analytics', label: 'Analytics' },
  { value: 'other', label: 'Other' },
];

// Lowercase letters, digits, ``-`` and ``_``; 2–64 chars. Matches the backend
// ``_SLUG_PATTERN`` so the user gets the same error client-side.
const SLUG_RULE = {
  required: 'Slug is required',
  pattern: {
    value: /^[a-z0-9][a-z0-9_-]{1,63}$/,
    message: "2–64 chars: lowercase letters, digits, '-' or '_'",
  },
};

interface AppIntegrationFormPageProps {
  integrationId?: string;
}

export default function AppIntegrationFormPage({ integrationId }: AppIntegrationFormPageProps) {
  const router = useRouter();
  const isEditMode = Boolean(integrationId);

  const [loading, setLoading] = useState(isEditMode);
  const [saving, setSaving] = useState(false);

  const { control, handleSubmit, reset } = useForm<FormState>({
    defaultValues: DEFAULT_STATE,
    mode: 'onBlur',
  });

  // Hydrate the form when editing an existing integration. Cancelled flag
  // guards against state updates after the user navigates away mid-load.
  useEffect(() => {
    if (!integrationId) return;
    let cancelled = false;
    setLoading(true);
    getAppIntegration(integrationId)
      .then((row) => {
        if (cancelled) return;
        reset(formStateFromRow(row));
      })
      .catch((err) => {
        if (!cancelled) handleApiError(err);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [integrationId, reset]);

  // Conditionally show OAuth-specific fields. ``useWatch`` (vs ``watch()``)
  // keeps the parent render-list stable; only the dependent block re-renders.
  const authType = useWatch({ control, name: 'auth_type' });
  const isOAuth = authType === 'oauth';

  const onSave = async (values: FormState) => {
    setSaving(true);
    try {
      const payload = serializePayload(values);
      if (isEditMode && integrationId) {
        await updateAppIntegration(integrationId, payload);
        showToast.success('Integration updated');
      } else {
        await createAppIntegration(payload);
        showToast.success('Integration created');
      }
      router.push('/settings/integrations');
    } catch (err) {
      handleApiError(err);
    } finally {
      setSaving(false);
    }
  };

  const onBack = useGoBack('/settings/integrations');

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
              <Section
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
              </Section>

              <Section
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
              </Section>

              <Section
                icon={<Settings2 size={14} className="text-muted-foreground" />}
                title="Configuration"
                description="Where credentials live and how this integration is exposed."
              >
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <TextInput
                    name="client_id_env_key"
                    control={control}
                    label="Client ID env var"
                    placeholder="HUBSPOT_MCP_CLIENT_ID"
                    helperText="Name of the env var holding the client_id."
                    className="font-mono"
                  />
                  <TextInput
                    name="client_secret_env_key"
                    control={control}
                    label="Client Secret env var"
                    placeholder="HUBSPOT_MCP_CLIENT_SECRET"
                    helperText="Optional for public PKCE clients."
                    className="font-mono"
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
              </Section>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────

interface SectionProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  children: React.ReactNode;
}

function Section({ icon, title, description, children }: SectionProps) {
  return (
    <section className="space-y-4 rounded-lg border border-border bg-background p-4">
      <div>
        <div className="flex items-center gap-2">
          {icon}
          <h2 className="text-[13px] font-semibold tracking-tight text-foreground">{title}</h2>
        </div>
        <p className="mt-0.5 text-[11.5px] text-muted-foreground">{description}</p>
      </div>
      <div className="space-y-4">{children}</div>
    </section>
  );
}

/**
 * Convert the persisted row into the flat string-based form shape. Done in
 * one place so the form fields don't have to special-case nullable columns.
 */
function formStateFromRow(row: AppIntegration): FormState {
  return {
    slug: row.slug ?? '',
    display_name: row.display_name ?? '',
    description: row.description ?? '',
    category: row.category ?? NO_CATEGORY,
    icon_url: row.icon_url ?? '',
    auth_type: row.auth_type ?? 'oauth',
    auth_url: row.auth_url ?? '',
    token_url: row.token_url ?? '',
    scopes: (row.scopes ?? []).join(', '),
    client_id_env_key: row.client_id_env_key ?? '',
    client_secret_env_key: row.client_secret_env_key ?? '',
    pkce_required: row.pkce_required,
    is_enabled: row.is_enabled,
    sort_order: row.sort_order ?? 100,
    extra_auth_params: row.extra_auth_params ? JSON.stringify(row.extra_auth_params, null, 2) : '',
  };
}

/**
 * Trim, parse, and shape the form values into the API payload.
 *
 * Empty strings become ``null`` for nullable fields so the server can tell
 * "cleared" apart from "untouched". ``scopes`` is split on commas or
 * newlines; ``extra_auth_params`` is parsed as JSON (throws a toast-friendly
 * error if malformed).
 */
function serializePayload(values: FormState): AppIntegrationCreatePayload {
  const scopes = values.scopes
    .split(/[,\n]/)
    .map((s) => s.trim())
    .filter(Boolean);

  let extraAuthParams: Record<string, unknown> | null = null;
  const rawExtras = values.extra_auth_params.trim();
  if (rawExtras) {
    try {
      const parsed = JSON.parse(rawExtras);
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        extraAuthParams = parsed as Record<string, unknown>;
      } else {
        throw new Error('Extra auth params must be a JSON object');
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Invalid JSON in extra auth params';
      throw Object.assign(new Error(msg), { response: { data: { detail: msg } } });
    }
  }

  return {
    slug: values.slug.trim().toLowerCase(),
    display_name: values.display_name.trim(),
    auth_type: values.auth_type,
    description: nullable(values.description),
    category: values.category === NO_CATEGORY ? null : nullable(values.category),
    icon_url: nullable(values.icon_url),
    auth_url: nullable(values.auth_url),
    token_url: nullable(values.token_url),
    scopes: scopes.length ? scopes : null,
    client_id_env_key: nullable(values.client_id_env_key),
    client_secret_env_key: nullable(values.client_secret_env_key),
    pkce_required: values.pkce_required,
    is_enabled: values.is_enabled,
    sort_order: Number(values.sort_order) || 100,
    extra_auth_params: extraAuthParams,
  };
}

function nullable(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}
