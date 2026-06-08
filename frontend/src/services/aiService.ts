import axiosInstance from '@/utils/axios';

export interface GeneratePromptPayload {
  agent_name?: string;
  agent_description?: string;
  agent_type?: string;
  instruction?: string;
}

export interface ImprovePromptPayload {
  text: string;
  agent_name?: string;
  agent_description?: string;
  agent_type?: string;
}

/** Generate a fresh agent system prompt from the agent's context. */
export const generateSystemPrompt = async (payload: GeneratePromptPayload): Promise<string> => {
  const { data } = await axiosInstance.post<{ text: string }>('/agent/generate_prompt', payload);
  return data.text ?? '';
};

/** Improve an existing agent system prompt. */
export const improveSystemPrompt = async (payload: ImprovePromptPayload): Promise<string> => {
  const { data } = await axiosInstance.post<{ text: string }>('/agent/improve_prompt', payload);
  return data.text ?? '';
};
