import axiosInstance from '@/utils/axios';

export const getAgents = async () => {
  const res = await axiosInstance.get('/agent/get_all_agents');
  return res.data;
};

/** Fetch a single agent by id. Returns the first item from get_all_agents?agent_id=id. */
export const getAgent = async (id: number | string) => {
  const res = await axiosInstance.get('/agent/get_all_agents', {
    params: { agent_id: Number(id) },
  });
  const data = Array.isArray(res.data) ? res.data : (res.data?.data ?? []);
  return data[0] ?? null;
};

/** Create or update agent. Send id in payload to update. */
export const upsertAgent = async (payload: Record<string, unknown>) => {
  const res = await axiosInstance.post('/agent/upsert_agent', payload);
  return res.data;
};
