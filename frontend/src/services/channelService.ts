import axiosInstance from '@/utils/axios';

export interface ChannelApiResponse {
  id: number;
  name: string;
  auth_token: string;
  account_sid: string;
  created_at: string;
}

interface TwilioMetaData {
  account_sid: string;
  auth_token: string;
}

export const getChannels = async (): Promise<ChannelApiResponse[]> => {
  const { data } = await axiosInstance.get<ChannelApiResponse[]>('/channel/list');
  return data ?? [];
};

export const upsertChannel = async (payload: {
  id?: number;
  name: string;
  type: 'TWILIO';
  meta_data: TwilioMetaData;
}): Promise<ChannelApiResponse> => {
  const { data } = await axiosInstance.post<ChannelApiResponse>('/channel/upsert', payload);
  return data;
};

export const deleteChannel = async (channelId: number): Promise<void> => {
  await axiosInstance.delete('/channel/delete', { params: { channel_id: channelId } });
};
