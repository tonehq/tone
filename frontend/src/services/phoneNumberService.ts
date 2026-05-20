import axiosInstance from '@/utils/axios';

export interface TwilioPhoneNumber {
  phone_number: string;
  friendly_name?: string;
  sid?: string;
}

export interface AssignedPhoneNumber {
  phone_number: string;
  agent_id: number;
  agent_name: string;
  provider: string;
}

export const getTwilioPhoneNumbers = async (
  type: string = 'twilio',
  agentId?: number,
  channelId?: number,
): Promise<TwilioPhoneNumber[]> => {
  const params: Record<string, string | number> = { type };
  if (agentId != null) params.agent_id = agentId;
  if (channelId != null) params.channel_id = channelId;
  const { data } = await axiosInstance.get<TwilioPhoneNumber[]>(
    '/channel_phone_number/get_twilio_phone_numbers',
    { params },
  );
  return data ?? [];
};

export const getAssignedPhoneNumbers = async (): Promise<AssignedPhoneNumber[]> => {
  const { data } = await axiosInstance.get<AssignedPhoneNumber[]>(
    '/agent_channel_phone_number/get_assigned_phone_numbers',
  );
  return data ?? [];
};
