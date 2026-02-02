import axiosInstance from "@/utils/axios"

export const getAgents = async () => {
    const res = await axiosInstance.get('/agent/get_all_agents');
    return res.data
}