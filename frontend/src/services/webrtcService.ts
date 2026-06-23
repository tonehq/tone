import axiosInstance from '@/utils/axios';

export interface WebCallSession {
  provider: string;
  room: string;
  url: string;
  token: string;
  client_url: string;
}

export const startWebCall = async (slug: string): Promise<WebCallSession> => {
  const res = await axiosInstance.post<WebCallSession>(`/webrtc/call/${slug}`);
  return res.data;
};
