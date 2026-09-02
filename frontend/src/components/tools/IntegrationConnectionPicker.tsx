'use client';

import { CustomLink, ScopeStatus, SelectInput } from '@/components/shared';
import { NO_APP_INTEGRATION, useIntegrationConnections } from '@/hooks/useIntegrationConnections';
import { useEffect, useMemo } from 'react';

interface IntegrationConnectionPickerProps {
  /** Currently selected catalog row. ``null`` shows every connection. */
  appIntegrationId: string | null;
  /** Currently selected OAuth connection. */
  oauthConnectionId: string | null;
  /** Provider slug whose required scopes are checked against the picked
   * connection (e.g. ``"google_calendar"`` for a built-in calendar tool).
   * Omit to suppress the scope-status widget entirely — appropriate for
   * custom tools, where the required scopes are unknowable. */
  requiredScopesProviderSlug?: string | null;
  /** When the picker mounts with no integration selected, auto-pick the
   * catalog row whose slug matches this — e.g. a Google Calendar tool lands
   * with the Google Calendar integration pre-selected. Pass ``null`` /
   * ``undefined`` to skip the auto-default. */
  autoDefaultIntegrationSlug?: string | null;
  onAppIntegrationIdChange: (id: string | null) => void;
  onOAuthConnectionIdChange: (id: string | null) => void;
  /** Fired on any picker change so the parent can mark the form dirty. */
  onDirty?: () => void;
}

/**
 * Two-picker block shared by every form that lets the user bind a tool, MCP
 * server, or webhook to an OAuth connection: "Linked integration" narrows
 * the connection list to a catalog entry; "OAuth connection" picks the
 * credential to use.
 *
 * Connection data is fetched (server-side filtered, race-safe) by
 * :func:`useIntegrationConnections` — there is no client-side filtering and
 * no N+1.
 */
export default function IntegrationConnectionPicker({
  appIntegrationId,
  oauthConnectionId,
  requiredScopesProviderSlug,
  autoDefaultIntegrationSlug,
  onAppIntegrationIdChange,
  onOAuthConnectionIdChange,
  onDirty,
}: IntegrationConnectionPickerProps) {
  const { appIntegrations, oauthConnections, catalog, connectionsLoading } =
    useIntegrationConnections(appIntegrationId);

  // Auto-default the integration to the catalog row matching the caller's
  // slug, but only when the user hasn't already picked one. Owned here so a
  // parent that wants this behaviour doesn't need its own
  // ``useIntegrationConnections`` call — that previously caused two hook
  // instances per form and doubled every fetch.
  useEffect(() => {
    if (!autoDefaultIntegrationSlug) return;
    if (appIntegrationId && appIntegrationId !== NO_APP_INTEGRATION) return;
    const match = appIntegrations.find((i) => i.slug === autoDefaultIntegrationSlug);
    if (match) onAppIntegrationIdChange(match.id);
  }, [autoDefaultIntegrationSlug, appIntegrations, appIntegrationId, onAppIntegrationIdChange]);

  const selectedConnection = useMemo(
    () => oauthConnections.find((c) => String(c.id) === String(oauthConnectionId)) ?? null,
    [oauthConnections, oauthConnectionId],
  );

  // Scopes the chosen connection should have, per the catalog. Only computed
  // when the caller explicitly pins a provider — custom tools, where the
  // required scopes are unknowable, pass ``null`` and get no widget.
  const requiredScopes = useMemo(
    () =>
      requiredScopesProviderSlug
        ? (catalog.find((p) => p.slug === requiredScopesProviderSlug)?.scopes ?? [])
        : [],
    [catalog, requiredScopesProviderSlug],
  );

  // Picker option lists. Sentinel-up-front for the integration picker; the
  // connection picker hides pending rows so the user can't bind to a
  // connection that still has no usable token — same filter we use in
  // ``oauth-connection-grid`` and ``MCPFormPage``.
  const appIntegrationOptions = useMemo(
    () => [
      { value: NO_APP_INTEGRATION, label: 'None — show all connections' },
      ...appIntegrations.map((i) => ({ value: i.id, label: i.display_name })),
    ],
    [appIntegrations],
  );
  const connectionOptions = useMemo(
    () =>
      oauthConnections
        .filter((c) => c.public_metadata?.status !== 'pending')
        .map((c) => ({
          value: String(c.id),
          label: `${c.public_metadata?.user_email ?? c.label ?? `Connection #${c.id}`} (${c.provider_slug})`,
        })),
    [oauthConnections],
  );

  const handleIntegrationChange = (value: string) => {
    onAppIntegrationIdChange(value && value !== NO_APP_INTEGRATION ? value : null);
    onDirty?.();
  };
  const handleConnectionChange = (value: string) => {
    onOAuthConnectionIdChange(value || null);
    onDirty?.();
  };

  return (
    <div className="space-y-5">
      <SelectInput
        name="integration-picker-app-integration"
        label="Linked integration"
        placeholder="None — show all connections"
        options={appIntegrationOptions}
        value={appIntegrationId ?? NO_APP_INTEGRATION}
        onValueChange={handleIntegrationChange}
        helperText="Filters the connected account list below to this integration only."
      />
      <div>
        <SelectInput
          name="integration-picker-oauth-connection"
          label="Connected Account"
          options={connectionOptions}
          value={oauthConnectionId ? String(oauthConnectionId) : ''}
          onValueChange={handleConnectionChange}
          loading={connectionsLoading}
          placeholder="Select an account..."
        />
        {selectedConnection && requiredScopes.length > 0 && (
          <div className="mt-2.5">
            <ScopeStatus
              granted={selectedConnection.public_metadata?.scopes}
              required={requiredScopes}
            />
          </div>
        )}
        {oauthConnections.length === 0 && !connectionsLoading && (
          <p className="mt-2 text-[12px] text-muted-foreground">
            No accounts connected for this integration.{' '}
            <CustomLink href="/settings/integrations" className="text-[12px] font-normal">
              Connect one in Integrations
            </CustomLink>
            .
          </p>
        )}
      </div>
    </div>
  );
}
