'use client';

import { listAppIntegrations } from '@/services/appIntegrationService';
import { getOAuthCatalog, getOAuthConnections } from '@/services/oauthService';
import type { AppIntegration } from '@/types/appIntegration';
import type { OAuthCatalogProvider, OAuthConnection } from '@/types/oauth';
import { handleApiError } from '@/utils/helpers';
import { useEffect, useState } from 'react';

/**
 * Sentinel for the "no integration selected" choice in a Radix `<Select>` —
 * Radix reserves the empty string for "clear selection", so picker forms use
 * this token in their form state and translate it to `null` on save.
 */
export const NO_APP_INTEGRATION = '__none__';

/**
 * Shared state owner for forms that pair an "App Integration" picker with an
 * "OAuth connection" picker (currently the MCP server form and the built-in
 * tool form). Owning this in one hook gives us:
 *
 *   - **DRY** — the catalog/integrations/connections fetch logic lives in
 *     exactly one place, so a fix in one form lands in every form.
 *   - **No N+1** — the catalog and the integrations list are fetched **once,
 *     in parallel**, on mount. Connections are fetched **server-side
 *     filtered** by the selected `app_integration_id`, so the dropdown never
 *     loads every connection in the org just to filter on the client.
 *   - **Race-safe** — when the user flips the picker rapidly, the in-flight
 *     fetch is ignored via a per-effect cancellation flag.
 *
 * The hook intentionally does NOT own which integration is selected — that
 * lives in the consumer's form state so the picker plays nicely with
 * react-hook-form. Pass the current selection in and the hook keeps the
 * connection list in sync.
 *
 * @param appIntegrationId  The currently selected integration. Pass
 *   `null` / `undefined` / `NO_APP_INTEGRATION` to show every connection.
 */
export interface UseIntegrationConnectionsResult {
  /** Enabled catalog rows the user can pick from. */
  appIntegrations: AppIntegration[];
  /** OAuth connections matching the current `appIntegrationId` filter. */
  oauthConnections: OAuthConnection[];
  /** OAuth catalog entries (provider slug → required scopes). */
  catalog: OAuthCatalogProvider[];
  /** True while the connection list is being refetched. */
  connectionsLoading: boolean;
}

export function useIntegrationConnections(
  appIntegrationId: string | null | undefined,
): UseIntegrationConnectionsResult {
  const [appIntegrations, setAppIntegrations] = useState<AppIntegration[]>([]);
  const [catalog, setCatalog] = useState<OAuthCatalogProvider[]>([]);
  const [oauthConnections, setOauthConnections] = useState<OAuthConnection[]>([]);
  const [connectionsLoading, setConnectionsLoading] = useState(false);

  // Fetch catalog + integrations once on mount, in parallel. These rarely
  // change during a form's lifetime so refetching on every picker change
  // would be wasteful — the OAuth connection list is the only piece that
  // needs to react to the filter.
  useEffect(() => {
    let cancelled = false;
    Promise.all([getOAuthCatalog(), listAppIntegrations({ page_size: 200 })])
      .then(([providers, integrations]) => {
        if (cancelled) return;
        setCatalog(providers);
        setAppIntegrations(integrations.rows.filter((r) => r.is_enabled));
      })
      .catch((error) => {
        if (!cancelled) handleApiError(error);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Refetch the connection list whenever the linked-integration picker
  // changes. The empty / sentinel value shows every connection (no server
  // filter); a real UUID narrows to that catalog entry only. Race guard
  // suppresses out-of-order responses if the user toggles quickly.
  useEffect(() => {
    let cancelled = false;
    const hasFilter = !!appIntegrationId && appIntegrationId !== NO_APP_INTEGRATION;
    const params = hasFilter ? { app_integration_id: appIntegrationId as string } : {};
    setConnectionsLoading(true);
    getOAuthConnections(params)
      .then((connections) => {
        if (!cancelled) setOauthConnections(connections);
      })
      .catch((error) => {
        if (!cancelled) handleApiError(error);
      })
      .finally(() => {
        if (!cancelled) setConnectionsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [appIntegrationId]);

  return { appIntegrations, oauthConnections, catalog, connectionsLoading };
}
