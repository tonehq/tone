import type { OAuthConnection, OAuthProviderStatus } from '@/types/oauth';
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
