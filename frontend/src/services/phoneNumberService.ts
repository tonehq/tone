import axiosInstance from '@/utils/axios';

export interface TwilioPhoneNumber {
  phone_number: string;
  friendly_name?: string;
  sid?: string;
}

export const getTwilioPhoneNumbers = async (
  type: string = 'twilio',
): Promise<TwilioPhoneNumber[]> => {
  const { data } = await axiosInstance.get<TwilioPhoneNumber[]>(
    '/channel_phone_number/get_twilio_phone_numbers',
    { params: { type } },
  );
  return data ?? [];
};
