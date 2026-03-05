export interface AgentGeneralFormData {
  name: string;
  description: string;
  aiModel: number | null;
  end_call_message: string;
  first_message: string;
  customVocabulary: string[];
  filterWords: string[];
  useRealisticFillerWords: boolean;
  llmMetaData: Record<string, unknown>;
}

export interface AgentVoiceFormData {
  language: string;
  voiceSpeed: number;
  voiceProvider: number | null;
  sttProvider: number | null;
  patienceLevel: 'low' | 'medium' | 'high';
  speechRecognition: 'fast' | 'accurate';
  ttsMetaData: Record<string, unknown>;
  sttMetaData: Record<string, unknown>;
}

export interface AgentCallConfigFormData {
  callRecording: boolean;
  callTranscription: boolean;
}
