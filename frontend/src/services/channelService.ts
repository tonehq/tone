import type { Channel, ChannelUpsertPayload } from '@/types/integration';
import axiosInstance from '@/utils/axios';

export interface ChannelListParams {
  channel_type?: string | null;
}

export const listChannels = async (params: ChannelListParams = {}): Promise<Channel[]> => {
  const body = { channel_type: params.channel_type ?? null };
  const { data } = await axiosInstance.post<{
    items: Channel[];
    total: number;
    page: number;
    page_size: number;
  }>('/channel/list', body);
  return data?.items ?? [];
};

export const getChannel = async (channelId: string, includeConfig = false): Promise<Channel> => {
  const { data } = await axiosInstance.get<Channel>('/channel/get', {
    params: { channel_id: channelId, include_config: includeConfig },
  });
  return data;
};

export const upsertChannel = async (payload: ChannelUpsertPayload): Promise<Channel> => {
  const { data } = await axiosInstance.post<Channel>('/channel/upsert', payload);
  return data;
};

export const deleteChannel = async (channelId: string): Promise<void> => {
  await axiosInstance.delete('/channel/delete', { params: { channel_id: channelId } });
};

export const getChannelsByType = async (type: string): Promise<Channel[]> => {
  const { data } = await axiosInstance.get<Channel[]>('/channel/list_by_type', {
    params: { type },
  });
  return data ?? [];
};

export interface ChannelPhoneNumber {
  id: string;
  number: string;
  label: string | null;
  channel_id: string;
  assigned_to: {
    agent_id: string;
    agent_name: string;
  } | null;
}

export const listChannelPhoneNumbers = async (channelId: string): Promise<ChannelPhoneNumber[]> => {
  const { data } = await axiosInstance.get<ChannelPhoneNumber[]>('/channel/phone_numbers', {
    params: { channel_id: channelId },
  });
  return data ?? [];
};

export const listTwilioPhoneNumbers = async (channelId: string): Promise<ChannelPhoneNumber[]> => {
  const { data } = await axiosInstance.get<ChannelPhoneNumber[]>('/channel/twilio_phone_numbers', {
    params: { channel_id: channelId },
  });
  return data ?? [];
};

export const listTelnyxPhoneNumbers = async (channelId: string): Promise<ChannelPhoneNumber[]> => {
  const { data } = await axiosInstance.get<ChannelPhoneNumber[]>('/channel/telnyx_phone_numbers', {
    params: { channel_id: channelId },
  });
  return data ?? [];
};
