import type { OAuthConnection, OAuthProviderStatus } from '@/types/oauth';
import axiosInstance from '@/utils/axios';

export const getOAuthConnections = async (): Promise<OAuthConnection[]> => {
  const { data } = await axiosInstance.get<OAuthConnection[]>('/oauth/connections');
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

export const disconnectOAuth = async (connectionId: number): Promise<void> => {
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
