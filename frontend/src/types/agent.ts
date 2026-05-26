export type AgentType = 'inbound' | 'outbound' | 'widget' | 'chat';

export type AgentStatus = 'active' | 'inactive' | 'draft';

export interface Agent {
  id: string;
  name: string;
  type: AgentType;
  status: AgentStatus;
  phoneNumber?: string;
  createdAt: string;
  lastEdited: string;
  avatar?: string;
}

export interface AgentFormData {
  name: string;
  image?: string;
  aiModel: string;
  timezone: string;
  knowledgeBase?: string;
  customVocabulary?: string[];
  language: string;
  voice: string;
  voiceProvider: string;
  sttProvider: string;
  patienceLevel: 'low' | 'medium' | 'high';
  speechRecognition: 'faster' | 'high_accuracy';
  voiceSpeed: number;
  voiceVolume: number;
  interruptionSensitivity: number;
  voicePrompting: string;
  filterWords?: string[];
  useRealisticFillerWords: boolean;
  maxCallDuration?: number;
  greeting?: string;
  endCallPhrase?: string;
  callRecording: boolean;
  callTranscription: boolean;
}

export interface CreateAgentModalOption {
  type: AgentType;
  title: string;
  description: string;
  icon: React.ReactNode;
}

export interface ApiAgent {
  id: number;
  uuid: string;
  name: string;
  description: string;
  agent_type?: string;
  phone_number?: { type: string; no: string }[];
  is_public: boolean;
  tags: Record<string, unknown>;
  total_calls: number;
  total_minutes: number;
  average_rating: number;
  created_by: number;
  created_at: number;
  updated_at: number;
  llm_account_id: number;
  tts_account_id: number;
  stt_account_id: number;
  llm_model_id: number | null;
  tts_model_id: number | null;
  stt_model_id: number | null;
  llm_model_instance_id?: number | null;
  tts_model_instance_id?: number | null;
  stt_model_instance_id?: number | null;
  llm_model_provider_menu_id?: number | null;
  tts_model_provider_menu_id?: number | null;
  stt_model_provider_menu_id?: number | null;
  llm_model_menu_id?: number | null;
  tts_model_menu_id?: number | null;
  stt_model_menu_id?: number | null;
  first_message: string;
  system_prompt: string;
  end_call_message: string;
  voicemail_message: string | null;
  status: string;
  custom_vocabulary: string | string[] | null;
  filter_words: string | string[] | null;
  realistic_filler_words: boolean | string | null;
  language: string | null;
  voice_speed: number | string | null;
  patience_level: string | null;
  speech_recognition: string | null;
  call_recording: boolean | string | null;
  call_transcription: boolean | string | null;
  channels?: any[] | null;
  [key: string]: unknown;
}

export interface AgentsState {
  agentList: ApiAgent[];
}

export interface ListAgentsParams {
  page?: number;
  page_size?: number;
  search?: string;
  sort_by?: string;
  is_active?: boolean;
  agent_type?: string;
}

export interface PaginatedAgents {
  items: ApiAgent[];
  total: number;
  page: number;
  page_size: number;
}

export interface PaginatedAgentsState {
  items: ApiAgent[];
  total: number;
  page: number;
  pageSize: number;
  loading: boolean;
}

export interface AgentFormState {
  name: string;
  description: string;
  end_call_message: string;
  first_message: string;
  customVocabulary: string[];
  filterWords: string[];
  language: string;
  patienceLevel: string;
  speechRecognition: string;
  voiceSpeed: number;
  voiceVolume: number;
  interruptionSensitivity: number;
  voicePrompting: string;
  useRealisticFillerWords: boolean;
  callRecording: boolean;
  callTranscription: boolean;
  phoneNumbers: { type: string; no: string }[];
  channels: any[];
  channelId: number | null;
  llmMetaData: Record<string, unknown>;
  ttsMetaData: Record<string, unknown>;
  sttMetaData: Record<string, unknown>;
  // Provider-based fields (model_providers_menu.id + model_menu.id)
  llmProviderMenuId: number | null;
  llmModelMenuId: number | null;
  ttsProviderMenuId: number | null;
  ttsModelMenuId: number | null;
  sttProviderMenuId: number | null;
  sttModelMenuId: number | null;
}
