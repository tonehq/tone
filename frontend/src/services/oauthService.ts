import type { OAuthCatalogProvider, OAuthConnection, OAuthProviderStatus } from '@/types/oauth';
import axiosInstance from '@/utils/axios';

export interface OAuthListParams {
  provider_slug?: string | null;
}

export const listOAuthConnections = async (
  params: OAuthListParams = {},
): Promise<OAuthConnection[]> => {
  const body = { provider_slug: params.provider_slug ?? null };
  const { data } = await axiosInstance.post<OAuthConnection[]>('/oauth/list', body);
  return data ?? [];
};

export const getOAuthConnections = async (provider?: string): Promise<OAuthConnection[]> => {
  const { data } = await axiosInstance.get<OAuthConnection[]>('/oauth/connections', {
    params: provider ? { provider } : undefined,
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
export const discoverMcpOAuth = async (serverUrl: string, label?: string): Promise<string> => {
  const { data } = await axiosInstance.post<{ auth_url: string; connection_id: string }>(
    '/oauth/mcp/discover',
    { server_url: serverUrl, label },
  );
  return data.auth_url;
};

export type CustomCredentialAuthKind = 'oauth2_client_credentials' | 'bearer';

export interface CustomCredentialPayload {
  name: string;
  auth_kind: CustomCredentialAuthKind;
  token_url?: string;
  client_id?: string;
  client_secret?: string;
  scope?: string;
  token?: string;
}

/** Create a user-defined credential (OAuth 2.0 client-credentials or static Bearer token). */
export const createCustomCredential = async (
  payload: CustomCredentialPayload,
): Promise<OAuthConnection> => {
  const { data } = await axiosInstance.post<OAuthConnection>('/oauth/custom_credential', payload);
  return data;
};
