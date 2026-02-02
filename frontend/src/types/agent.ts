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
  // Basic Details
  name: string;
  image?: string;
  aiModel: string;
  timezone: string;
  knowledgeBase?: string;
  customVocabulary?: string[];
  
  // Voice Configuration
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
  
  // Call Configuration
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
