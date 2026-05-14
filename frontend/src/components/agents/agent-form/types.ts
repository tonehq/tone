export interface AgentGeneralFormData {
  name: string;
  description: string;
  end_call_message: string;
  first_message: string;
  customVocabulary: string[];
  filterWords: string[];
  useRealisticFillerWords: boolean;
  llmMetaData: Record<string, unknown>;
  llmProviderMenuId: number | null;
  llmModelMenuId: number | null;
}

export interface AgentVoiceFormData {
  language: string;
  voiceSpeed: number;
  patienceLevel: 'low' | 'medium' | 'high';
  speechRecognition: 'fast' | 'accurate';
  ttsMetaData: Record<string, unknown>;
  sttMetaData: Record<string, unknown>;
  ttsProviderMenuId: number | null;
  ttsModelMenuId: number | null;
  sttProviderMenuId: number | null;
  sttModelMenuId: number | null;
}

export interface AgentCallConfigFormData {
  callRecording: boolean;
  callTranscription: boolean;
}
