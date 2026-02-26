import type { ServiceProvider } from '@/types/provider';
import axiosInstance from '@/utils/axios';

export type { ServiceProvider, ServiceProviderModel } from '@/types/provider';

export const getServiceProviders = async (): Promise<ServiceProvider[]> => {
  const { data } = await axiosInstance.get<ServiceProvider[]>('/service-providers/list');
  return data ?? [];
};
