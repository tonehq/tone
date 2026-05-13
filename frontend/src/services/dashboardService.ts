import axiosInstance from '@/utils/axios';

export interface DashboardStats {
  total_agents: number;
  active_calls: number;
  minutes_used: number;
  success_rate: number;
}

export const getDashboardStats = async (): Promise<DashboardStats> => {
  const res = await axiosInstance.get('/dashboard/stats');
  return res.data;
};
