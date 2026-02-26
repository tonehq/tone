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
  custom_vocabulary: string | string[] | null;
  filter_words: string | string[] | null;
  realistic_filler_words: boolean | string | null;
  language: string | null;
  voice_speed: number | string | null;
  patience_level: string | null;
  speech_recognition: string | null;
  call_recording: boolean | string | null;
  call_transcription: boolean | string | null;
  [key: string]: unknown;
}

export interface AgentsState {
  agentList: ApiAgent[];
}

export interface AgentFormState {
  name: string;
  description: string;
  aiModel: number | null;
  end_call_message: string;
  first_message: string;
  customVocabulary: string[];
  filterWords: string[];
  language: string;
  voiceProvider: number | null;
  sttProvider: number | null;
  patienceLevel: string;
  speechRecognition: string;
  voiceSpeed: number;
  voiceVolume: number;
  interruptionSensitivity: number;
  voicePrompting: string;
  useRealisticFillerWords: boolean;
  callRecording: boolean;
  callTranscription: boolean;
}
