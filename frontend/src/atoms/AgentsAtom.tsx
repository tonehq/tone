import { getAgents } from '@/services/agentsService';
import { atom } from 'jotai';

export interface Agent {
  id: number;
  uuid: string;
  name: string;
  description: string;
  agent_type?: string;
  phone_number?: string;
  is_public: boolean;
  tags: Record<string, unknown>;
  total_calls: number;
  total_minutes: number;
  average_rating: number;
  created_by: number;
  created_at: number;
  updated_at: number;
  llm_service_id: number;
  tts_service_id: number;
  stt_service_id: number;
  llm_model_id: number | null;
  tts_model_id: number | null;
  stt_model_id: number | null;
  first_message: string;
  system_prompt: string;
  end_call_message: string;
  voicemail_message: string | null;
  status: string;
  custom_vocabulary: string | null;
  filter_words: string | null;
  realistic_filler_words: string | null;
  language: string | null;
  voice_speed: string | null;
  patience_level: string | null;
  speech_recognition: string | null;
  call_recording: string | null;
  call_transcription: string | null;
}

export interface AgentsState {
  agentList: Agent[];
}

const agentsAtom = atom<AgentsState>({
  agentList: [],
});

export const fetchAgentList = atom(null, async (_get, set) => {
  const res = await getAgents();
  if (Array.isArray(res)) {
    set(agentsAtom, (prev) => ({
      ...prev,
      agentList: res as Agent[],
    }));
  } else if (res && Array.isArray(res.data)) {
    set(agentsAtom, (prev) => ({
      ...prev,
      agentList: res.data as Agent[],
    }));
  } else {
    set(agentsAtom, (prev) => ({ ...prev, agentList: [] }));
  }
});

export default agentsAtom;
