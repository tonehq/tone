import type { OAuthCatalogProvider, OAuthConnection, OAuthProviderStatus } from '@/types/oauth';
import axiosInstance from '@/utils/axios';

export interface OAuthListParams {
  provider_slug?: string | null;
  /** When set, limits results to connections linked to this app_integrations row. */
  app_integration_id?: string | null;
}

export const listOAuthConnections = async (
  params: OAuthListParams = {},
): Promise<OAuthConnection[]> => {
  const body = {
    provider_slug: params.provider_slug ?? null,
    app_integration_id: params.app_integration_id ?? null,
  };
  const { data } = await axiosInstance.post<OAuthConnection[]>('/oauth/list', body);
  return data ?? [];
};

export interface GetOAuthConnectionsParams {
  provider?: string;
  app_integration_id?: string;
}

export const getOAuthConnections = async (
  params: GetOAuthConnectionsParams | string = {},
): Promise<OAuthConnection[]> => {
  // Back-compat: callers used to pass a single ``provider`` string.
  const query =
    typeof params === 'string'
      ? { provider: params }
      : {
          ...(params.provider ? { provider: params.provider } : {}),
          ...(params.app_integration_id ? { app_integration_id: params.app_integration_id } : {}),
        };

  const { data } = await axiosInstance.get<OAuthConnection[]>('/oauth/connections', {
    params: Object.keys(query).length ? query : undefined,
  });
  return data;
};

export const getOAuthConnectionByProvider = async (
  provider: string,
): Promise<OAuthProviderStatus> => {
  const { data } = await axiosInstance.get<OAuthProviderStatus>('/oauth/connection', {
    params: { provider },
  });
  return data;
};

export const disconnectOAuth = async (connectionId: string): Promise<void> => {
  await axiosInstance.delete('/oauth/disconnect', { params: { connection_id: connectionId } });
};

export const getOAuthProviders = async (): Promise<string[]> => {
  const { data } = await axiosInstance.get<{ providers: string[] }>('/oauth/providers');
  return data.providers;
};

export const getOAuthAuthorizeUrl = async (provider: string): Promise<string> => {
  const { data } = await axiosInstance.get<{ auth_url: string }>(`/oauth/${provider}/authorize`);
  return data.auth_url;
};

export const getOAuthCatalog = async (): Promise<OAuthCatalogProvider[]> => {
  const { data } = await axiosInstance.get<{ providers: OAuthCatalogProvider[] }>('/oauth/catalog');
  return data.providers ?? [];
};

/**
 * Generic MCP OAuth 2.1 discovery: probes a server, dynamically registers a client, and returns
 * the authorize URL to redirect the user to. Works with any spec-compliant remote MCP server.
 */
export const discoverMcpOAuth = async (
  serverUrl: string,
  label?: string,
  returnTo?: string,
  appIntegrationId?: string,
): Promise<string> => {
  const { data } = await axiosInstance.post<{ auth_url: string; connection_id: string }>(
    '/oauth/mcp/discover',
    {
      server_url: serverUrl,
      label,
      return_to: returnTo,
      app_integration_id: appIntegrationId ?? null,
    },
  );
  return data.auth_url;
};

export type CustomCredentialAuthKind = 'oauth2_client_credentials' | 'bearer' | 'api_key';

export interface CustomCredentialPayload {
  name: string;
  auth_kind: CustomCredentialAuthKind;
  token_url?: string;
  client_id?: string;
  client_secret?: string;
  scope?: string;
  token?: string;
  /** API-key credentials: the raw key and the header it is applied to. */
  api_key?: string;
  header_name?: string;
}

/** Create a user-defined credential (OAuth 2.0 client-credentials, static Bearer
 * token, or raw API key applied to a custom header). */
export const createCustomCredential = async (
  payload: CustomCredentialPayload,
): Promise<OAuthConnection> => {
  const { data } = await axiosInstance.post<OAuthConnection>('/oauth/custom_credential', payload);
  return data;
};
